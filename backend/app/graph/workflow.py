# backend/app/graph/workflow.py
"""
LangGraph workflow for Neural Analytics 3.0

This is the core orchestration layer that routes questions through
different agents based on intent and requirements.
"""
import os
import time
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.models.state import AnalyticsState, IntentClassification
from app.agents import SQLGeneratorAgent, SummaryAgent, AnomalyAgent, ForecastAgent
from app.tools.sql_tools import execute_sql_with_agent

# Import existing modules for compatibility
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from query_executor import execute_query, execute_upload_query
from chart_generator import generate_chart_spec
from category_translator import translate_categories

load_dotenv()


class AnalyticsWorkflow:
    """
    LangGraph-powered workflow for analytics queries.
    
    Workflow:
    1. Intent Classification → Determine what the user wants
    2. Schema Retrieval → Get relevant database context
    3. SQL Generation → Generate query using agent
    4. SQL Validation → Check query safety
    5. Query Execution → Run against database
    6. Error Repair → Auto-fix if query fails
    7. Post-processing → Translation, charting
    8. Analysis → Summary, anomalies, forecasting
    9. Response Building → Compose final response
    """
    
    def __init__(self):
        self.sql_agent = SQLGeneratorAgent()
        self.summary_agent = SummaryAgent()
        self.anomaly_agent = AnomalyAgent()
        self.forecast_agent = ForecastAgent()
        
        # Intent classifier
        self.intent_llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.intent_parser = PydanticOutputParser(pydantic_object=IntentClassification)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        workflow = StateGraph(AnalyticsState)
        
        # Add nodes
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("execute_query", self.execute_query_node)
        workflow.add_node("repair_sql", self.repair_sql_node)
        workflow.add_node("post_process", self.post_process_node)
        workflow.add_node("generate_summary", self.generate_summary_node)
        workflow.add_node("detect_anomalies", self.detect_anomalies_node)
        workflow.add_node("generate_forecast", self.generate_forecast_node)
        workflow.add_node("build_response", self.build_response_node)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_after_intent,
            {
                "sql": "generate_sql",
                "end": END
            }
        )
        
        workflow.add_edge("generate_sql", "execute_query")
        
        workflow.add_conditional_edges(
            "execute_query",
            self.route_after_execution,
            {
                "success": "post_process",
                "retry": "repair_sql",
                "fail": END
            }
        )
        
        workflow.add_edge("repair_sql", "execute_query")
        workflow.add_edge("post_process", "generate_summary")
        
        workflow.add_conditional_edges(
            "generate_summary",
            self.route_after_summary,
            {
                "anomaly": "detect_anomalies",
                "forecast": "generate_forecast",
                "end": "build_response"
            }
        )
        
        workflow.add_edge("detect_anomalies", "build_response")
        workflow.add_edge("generate_forecast", "build_response")
        workflow.add_edge("build_response", END)
        
        return workflow.compile()
    
    # ========== NODE IMPLEMENTATIONS ==========
    
    def classify_intent_node(self, state: AnalyticsState) -> AnalyticsState:
        """Classify user intent to route to appropriate workflow"""
        
        question = state["question"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for an analytics system.

Classify the user's question into one of these intents:
- sql_query: User wants to query data
- forecast: User wants time-series predictions
- anomaly: User wants to detect outliers
- summary: User just wants a summary of existing data

Determine if SQL execution, forecasting, or anomaly detection is needed.

Your response must be valid JSON matching the IntentClassification schema."""),
            ("human", "Question: {question}\n\n{format_instructions}")
        ])
        
        chain = prompt | self.intent_llm | self.intent_parser
        
        try:
            result = chain.invoke({
                "question": question,
                "format_instructions": self.intent_parser.get_format_instructions()
            })
            
            state["intent"] = result.intent
            state["source"] = "langchain_workflow"
            
        except Exception as e:
            # Default to SQL query on error
            state["intent"] = "sql_query"
            print(f"Intent classification error: {str(e)}")
        
        return state
    
    def generate_sql_node(self, state: AnalyticsState) -> AnalyticsState:
        """Generate SQL query using the SQL agent"""
        
        table_names = state.get("table_names")
        
        if table_names:
            # User-uploaded tables
            state = self.sql_agent.generate_sql_for_uploads(state)
        else:
            # Olist database
            state = self.sql_agent.generate_sql_for_olist(state)
        
        return state
    
    def execute_query_node(self, state: AnalyticsState) -> AnalyticsState:
        """Execute the generated SQL query"""
        
        sql = state.get("sql")
        table_names = state.get("table_names")
        
        if not sql:
            state["error"] = "No SQL query to execute"
            return state
        
        try:
            if table_names:
                # Execute against uploads schema
                result = execute_upload_query(sql, table_names)
            else:
                # Execute against olist schema
                result = execute_query(sql)
            
            if "error" in result:
                state["error"] = result["error"]
            else:
                state["data"] = result
                state["rows"] = result.get("rows", [])
                state["columns"] = result.get("columns", [])
                state["row_count"] = result.get("row_count", 0)
                state["error"] = None
                
        except Exception as e:
            state["error"] = str(e)
        
        return state
    
    def repair_sql_node(self, state: AnalyticsState) -> AnalyticsState:
        """Attempt to repair failed SQL query"""
        
        retry_count = state.get("retry_count", 0)
        
        if retry_count >= 2:
            state["error"] = "Max retries exceeded"
            return state
        
        # Use LLM to fix the SQL
        error_message = state.get("error", "")
        original_sql = state.get("sql", "")
        question = state["question"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a PostgreSQL expert. Fix the failing query.

Return ONLY the corrected SQL query, nothing else."""),
            ("human", """Original question: {question}

Failed SQL:
{sql}

Error:
{error}

Fix the query and return only the corrected SQL.""")
        ])
        
        chain = prompt | self.intent_llm
        
        try:
            result = chain.invoke({
                "question": question,
                "sql": original_sql,
                "error": error_message
            })
            
            fixed_sql = result.content.strip()
            
            # Clean the SQL
            if "```" in fixed_sql:
                import re
                match = re.search(r'```(?:sql)?\s*(.*?)\s*```', fixed_sql, re.DOTALL)
                if match:
                    fixed_sql = match.group(1)
            
            state["sql"] = fixed_sql
            state["retry_count"] = retry_count + 1
            state["error"] = None
            
        except Exception as e:
            state["error"] = f"Repair failed: {str(e)}"
        
        return state
    
    def post_process_node(self, state: AnalyticsState) -> AnalyticsState:
        """Post-process query results (translation, charting)"""
        
        rows = state.get("rows", [])
        columns = state.get("columns", [])
        
        if not rows:
            return state
        
        # Apply category translation for Olist queries
        if not state.get("table_names"):
            translated_rows = translate_categories(rows, columns)
            state["rows"] = translated_rows
            state["data"]["rows"] = translated_rows
        
        # Generate chart specification
        try:
            chart_spec = generate_chart_spec(
                state["data"],
                state["question"]
            )
            state["chart_spec"] = chart_spec
        except Exception as e:
            print(f"Chart generation error: {str(e)}")
            state["chart_spec"] = None
        
        return state
    
    def generate_summary_node(self, state: AnalyticsState) -> AnalyticsState:
        """Generate executive summary"""
        return self.summary_agent.generate_summary(state)
    
    def detect_anomalies_node(self, state: AnalyticsState) -> AnalyticsState:
        """Detect anomalies in results"""
        return self.anomaly_agent.detect_anomalies(state)
    
    def generate_forecast_node(self, state: AnalyticsState) -> AnalyticsState:
        """Generate time-series forecast"""
        return self.forecast_agent.generate_forecast(state)
    
    def build_response_node(self, state: AnalyticsState) -> AnalyticsState:
        """Build final response"""
        
        # Calculate execution time if not set
        if not state.get("execution_time_ms"):
            state["execution_time_ms"] = 0.0
        
        return state
    
    # ========== ROUTING FUNCTIONS ==========
    
    def route_after_intent(self, state: AnalyticsState) -> Literal["sql", "end"]:
        """Route based on classified intent"""
        intent = state.get("intent", "sql_query")
        
        if intent in ["sql_query", "forecast", "anomaly"]:
            return "sql"
        else:
            return "end"
    
    def route_after_execution(
        self,
        state: AnalyticsState
    ) -> Literal["success", "retry", "fail"]:
        """Route based on execution result"""
        
        error = state.get("error")
        retry_count = state.get("retry_count", 0)
        
        if not error:
            return "success"
        elif retry_count < 2:
            return "retry"
        else:
            return "fail"
    
    def route_after_summary(
        self,
        state: AnalyticsState
    ) -> Literal["anomaly", "forecast", "end"]:
        """Route to additional analysis if requested"""
        
        question_lower = state["question"].lower()
        
        if "anomaly" in question_lower or "outlier" in question_lower:
            return "anomaly"
        elif "forecast" in question_lower or "predict" in question_lower:
            return "forecast"
        else:
            return "end"
    
    # ========== PUBLIC API ==========
    
    def process_question(
        self,
        question: str,
        table_names: list = None
    ) -> dict:
        """
        Process a natural language question through the workflow.
        
        Args:
            question: Natural language question
            table_names: Optional list of table names for uploaded data
        
        Returns:
            Complete response dict with SQL, data, charts, summary, etc.
        """
        
        start_time = time.time()
        
        # Initialize state
        initial_state: AnalyticsState = {
            "question": question,
            "table_names": table_names,
            "schema_context": None,
            "relevant_tables": None,
            "sql": None,
            "sql_explanation": None,
            "data": None,
            "columns": None,
            "rows": None,
            "row_count": None,
            "error": None,
            "retry_count": 0,
            "chart_spec": None,
            "summary": None,
            "anomalies": None,
            "forecast": None,
            "execution_time_ms": None,
            "source": None,
            "intent": None,
        }
        
        # Run the workflow
        try:
            final_state = self.graph.invoke(initial_state)
            
            execution_time_ms = round((time.time() - start_time) * 1000, 2)
            
            # Build response
            response = {
                "question": question,
                "sql": final_state.get("sql"),
                "explanation": final_state.get("sql_explanation"),
                "data": final_state.get("data"),
                "chart_spec": final_state.get("chart_spec"),
                "summary": final_state.get("summary"),
                "anomalies": final_state.get("anomalies"),
                "forecast": final_state.get("forecast"),
                "meta": {
                    "execution_time_ms": execution_time_ms,
                    "source": final_state.get("source", "langchain_workflow"),
                    "intent": final_state.get("intent"),
                    "row_count": final_state.get("row_count", 0),
                    "chart_available": final_state.get("chart_spec") is not None,
                },
                "error": final_state.get("error")
            }
            
            return response
            
        except Exception as e:
            return {
                "question": question,
                "error": f"Workflow execution failed: {str(e)}",
                "meta": {
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "source": "langchain_workflow",
                }
            }


# Singleton instance
_workflow_instance = None


def get_workflow() -> AnalyticsWorkflow:
    """Get or create the workflow instance"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = AnalyticsWorkflow()
    return _workflow_instance

# Made with Bob
