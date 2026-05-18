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
from app.agents.metadata_agent import MetadataAgent
from app.tools.sql_tools import execute_sql_with_agent
from app.memory import get_memory_manager, get_greeting_prompt, get_name_introduction_prompt, get_casual_chat_prompt, get_out_of_scope_prompt
from app.memory.memory_summarizer import get_summarizer

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
        self.metadata_agent = MetadataAgent()
        
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
        workflow.add_node("handle_greeting", self.handle_greeting_node)
        workflow.add_node("handle_metadata", self.handle_metadata_node)  # NEW
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
                "greeting": "handle_greeting",
                "metadata": "handle_metadata",  # NEW
                "sql": "generate_sql",
                "end": END
            }
        )
        
        # Greeting and metadata go directly to build_response
        workflow.add_edge("handle_greeting", "build_response")
        workflow.add_edge("handle_metadata", "build_response")  # NEW
        
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
        
        # Get available tables/datasets for context
        table_names = state.get("table_names", [])
        has_data = bool(table_names)
        
        data_context = ""
        if has_data:
            data_context = f"\n\nAvailable datasets: {', '.join(table_names)}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for a DATA ANALYTICS system.

IMPORTANT: This system ONLY handles data analysis questions. Detect out-of-scope questions.

Classify the user's question into one of these intents:
- greeting: Simple greetings like "hi", "hello", "hey"
- name_introduction: User introducing themselves ("my name is X", "I'm X", "call me X")
- casual_chat: Questions about system capabilities ("what can you do", "help")
- metadata: Questions about dataset structure (columns, data types, shape, missing values, preview, statistics)
- sql_query: User wants to query/analyze their uploaded data
- forecast: User wants time-series predictions on their data
- anomaly: User wants to detect outliers in their data
- knowledge_graph: User wants to build a knowledge graph from their data
- summary: User wants a summary of their data
- out_of_scope: Questions about topics OUTSIDE data analytics (weather, sports, news, general knowledge, etc.)

METADATA QUERY EXAMPLES:
- "Show me all column names and their data types" → metadata
- "What is the shape of my dataset?" → metadata
- "Are there any missing values?" → metadata
- "Show me the first 10 rows" → metadata
- "Give me summary statistics" → metadata
- "What columns do I have?" → metadata
- "How many rows and columns?" → metadata

OUT OF SCOPE EXAMPLES:
- "What's the weather today?" → out_of_scope (weather)
- "Who won the game?" → out_of_scope (sports)
- "Tell me about history" → out_of_scope (general knowledge)
- "What's the capital of France?" → out_of_scope (geography)
- "How do I cook pasta?" → out_of_scope (cooking)

IN SCOPE EXAMPLES:
- "Show me sales trends" → sql_query
- "Detect anomalies in revenue" → anomaly
- "Forecast next month's orders" → forecast
- "What's in my dataset?" → summary

If the question is clearly about a topic unrelated to data analysis, mark it as out_of_scope and provide a rejection_reason.{data_context}

Your response must be valid JSON matching the IntentClassification schema."""),
            ("human", "Question: {question}\n\n{format_instructions}")
        ])
        
        chain = prompt | self.intent_llm | self.intent_parser
        
        try:
            result = chain.invoke({
                "question": question,
                "data_context": data_context,
                "format_instructions": self.intent_parser.get_format_instructions()
            })
            
            state["intent"] = result.intent
            state["source"] = "langchain_workflow"
            
            # Store out-of-scope info if detected
            if result.intent == "out_of_scope":
                state["error"] = result.rejection_reason or "This question is outside the scope of data analytics."
            
        except Exception as e:
            # Default to SQL query on error
            state["intent"] = "sql_query"
            print(f"Intent classification error: {str(e)}")
        
        return state
    
    def handle_metadata_node(self, state: AnalyticsState) -> AnalyticsState:
        """Handle metadata queries about dataset structure"""
        return self.metadata_agent.answer_metadata_question(state)
    
    def handle_greeting_node(self, state: AnalyticsState) -> AnalyticsState:
        """Handle greetings, introductions, casual chat, and out-of-scope rejections"""
        
        question = state["question"]
        intent = state.get("intent", "greeting")
        user_profile = state.get("user_profile", {})
        conversation_history = state.get("conversation_history", [])
        
        # Handle out-of-scope questions
        if intent == "out_of_scope":
            # Extract topic from question for better rejection message
            topic = "that topic"
            question_lower = question.lower()
            if any(word in question_lower for word in ["weather", "temperature", "rain", "sunny"]):
                topic = "weather"
            elif any(word in question_lower for word in ["sport", "game", "match", "score"]):
                topic = "sports"
            elif any(word in question_lower for word in ["news", "current events", "politics"]):
                topic = "news and current events"
            elif any(word in question_lower for word in ["cook", "recipe", "food"]):
                topic = "cooking"
            elif any(word in question_lower for word in ["history", "historical"]):
                topic = "history"
            
            prompt_text = get_out_of_scope_prompt(question, topic, user_profile, conversation_history)
            
            try:
                response = self.intent_llm.invoke(prompt_text)
                response_text = response.content if hasattr(response, 'content') else str(response)
                state["summary"] = response_text
                state["response"] = response_text
            except Exception as e:
                print(f"[Out-of-Scope Handler] Error: {e}")
                user_name = user_profile.get("name") if user_profile else None
                name_part = f"{user_name}, " if user_name else ""
                state["summary"] = f"I'm sorry {name_part}but I can only help with data analytics questions. I specialize in analyzing your uploaded datasets, creating visualizations, detecting anomalies, and forecasting trends. Would you like to explore your data instead?"
                state["response"] = state["summary"]
            
            return state
        
        # Get appropriate prompt based on intent
        if intent == "name_introduction":
            prompt_text = get_name_introduction_prompt(question)
            
            # Extract name from message
            summarizer = get_summarizer()
            extracted_name = summarizer.extract_name_from_message(question)
            
            if extracted_name:
                # Update user profile in state
                if not user_profile:
                    user_profile = {}
                user_profile["name"] = extracted_name
                state["user_profile"] = user_profile
                
                # Store in memory
                session_id = state.get("session_id")
                if session_id:
                    memory = get_memory_manager()
                    memory.add_conversation_turn(
                        session_id=session_id,
                        user_message=question,
                        assistant_response="",  # Will be filled after generation
                        intent=intent,
                        extracted_facts={"user_name": extracted_name}
                    )
        
        elif intent == "casual_chat":
            prompt_text = get_casual_chat_prompt(question, user_profile, conversation_history)
        else:
            # greeting
            prompt_text = get_greeting_prompt(question, user_profile, conversation_history)
        
        # Generate response using LLM
        try:
            response = self.intent_llm.invoke(prompt_text)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            state["summary"] = response_text
            state["response"] = response_text
            
        except Exception as e:
            print(f"[Greeting Handler] Error: {e}")
            user_name = user_profile.get("name") if user_profile else None
            if intent == "name_introduction" and user_name:
                state["summary"] = f"Nice to meet you, {user_name}! I'm Neural Analytics 2.0, your AI analytics assistant. What would you like to analyze today?"
            elif user_name:
                state["summary"] = f"Hi {user_name}! How can I help you today?"
            else:
                state["summary"] = "Hi! How can I help you today? I can analyze your data, create visualizations, detect anomalies, and more."
            state["response"] = state["summary"]
        
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
    
    def route_after_intent(self, state: AnalyticsState) -> Literal["greeting", "metadata", "sql", "end"]:
        """Route based on classified intent"""
        intent = state.get("intent", "sql_query")
        
        # Route conversational intents and out-of-scope to greeting handler
        if intent in ["greeting", "name_introduction", "casual_chat", "out_of_scope"]:
            return "greeting"
        # Route metadata queries to metadata handler
        elif intent == "metadata":
            return "metadata"
        # Route analytical intents to SQL generation
        elif intent in ["sql_query", "forecast", "anomaly", "knowledge_graph"]:
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
        table_names: list = None,
        session_id: str = None,
        conversation_history: list = None,
        user_profile: dict = None
    ) -> dict:
        """
        Process a natural language question through the workflow.
        
        Args:
            question: Natural language question
            table_names: Optional list of table names for uploaded data
            session_id: Session ID for conversation memory
            conversation_history: Previous conversation turns
            user_profile: User profile with name and preferences
        
        Returns:
            Complete response dict with SQL, data, charts, summary, etc.
        """
        
        start_time = time.time()
        
        # Initialize state
        initial_state: AnalyticsState = {
            "question": question,
            "table_names": table_names,
            "document_ids": None,
            "session_id": session_id,
            "conversation_history": conversation_history or [],
            "user_profile": user_profile or {},
            "key_findings": [],
            "conversation_summary": None,
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
            "knowledge_graph": None,
            "sources": None,
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
