# backend/app/agents/sql_agent.py
"""
SQL Agent using LangChain with structured outputs
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.models.state import SQLResponse, AnalyticsState
from app.tools.sql_tools import (
    get_table_schema,
    list_available_tables,
    validate_sql_query
)

load_dotenv()


class SQLGeneratorAgent:
    """
    Agent that generates SQL queries with structured outputs.
    Uses LangChain with Pydantic for guaranteed JSON responses.
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.0):
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.parser = PydanticOutputParser(pydantic_object=SQLResponse)
    
    def generate_sql_for_olist(self, state: AnalyticsState) -> AnalyticsState:
        """
        Generate SQL for Olist database queries.
        
        Uses focused prompts with schema context.
        """
        question = state["question"]
        
        # Get available tables
        tables = list_available_tables("olist")
        
        # Build schema context (focused on relevant tables)
        schema_context = self._get_relevant_schema(question, tables, "olist")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_olist_system_prompt()),
            ("human", """Question: {question}

Available Schema:
{schema_context}

Generate a PostgreSQL query to answer this question.

{format_instructions}""")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "question": question,
                "schema_context": schema_context,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Validate the generated SQL
            validation = validate_sql_query(result.sql, "olist")
            
            if not validation["valid"]:
                state["error"] = f"Invalid SQL: {validation['error_message']}"
                return state
            
            state["sql"] = result.sql
            state["sql_explanation"] = result.explanation
            state["schema_context"] = schema_context
            state["error"] = None
            
        except Exception as e:
            state["error"] = f"SQL generation failed: {str(e)}"
        
        return state
    
    def generate_sql_for_uploads(self, state: AnalyticsState) -> AnalyticsState:
        """
        Generate SQL for user-uploaded tables.
        
        Supports single or multi-table queries.
        """
        question = state["question"]
        table_names = state.get("table_names", [])
        
        if not table_names:
            state["error"] = "No table names provided for uploads query"
            return state
        
        # Get schema for specified tables
        schema_parts = []
        for table_name in table_names:
            schema = get_table_schema(table_name, "uploads")
            schema_parts.append(f"Table: uploads.{table_name}\n{schema}")
        
        schema_context = "\n\n".join(schema_parts)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_uploads_system_prompt(table_names)),
            ("human", """Question: {question}

Available Schema:
{schema_context}

Generate a PostgreSQL query to answer this question.

{format_instructions}""")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "question": question,
                "schema_context": schema_context,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Validate the generated SQL
            validation = validate_sql_query(result.sql, "uploads")
            
            if not validation["valid"]:
                state["error"] = f"Invalid SQL: {validation['error_message']}"
                return state
            
            # Ensure only allowed tables are referenced
            if not self._validate_table_references(result.sql, table_names):
                state["error"] = "SQL references unauthorized tables"
                return state
            
            state["sql"] = result.sql
            state["sql_explanation"] = result.explanation
            state["schema_context"] = schema_context
            state["error"] = None
            
        except Exception as e:
            state["error"] = f"SQL generation failed: {str(e)}"
        
        return state
    
    def _get_olist_system_prompt(self) -> str:
        """System prompt for Olist database queries"""
        return """You are a senior PostgreSQL analyst for Olist Brazilian e-commerce.

STRICT RULES:
1. Return ONLY valid PostgreSQL queries
2. Always use fully qualified names: olist.orders, olist.products, etc.
3. Always alias tables (o, p, oi, c, etc.)
4. Always qualify joins (oi.product_id = p.product_id)
5. Add LIMIT 200 at the end
6. Use proper date filtering with timestamp casting
7. Handle NULL values appropriately

CRITICAL FOR PRODUCT CATEGORIES:
- Product category names are in olist.products.product_category_name
- They are in Portuguese but will be translated to English after query execution
- To get categories by sales, JOIN order_items with products

Your response must be valid JSON matching the SQLResponse schema."""
    
    def _get_uploads_system_prompt(self, table_names: List[str]) -> str:
        """System prompt for uploaded table queries"""
        allowed_tables = ", ".join(f'uploads."{t}"' for t in table_names)
        
        return f"""You are a senior PostgreSQL analyst analyzing user-uploaded data.

STRICT RULES:
1. Return ONLY valid PostgreSQL queries
2. ONLY query these tables: {allowed_tables}
3. Use fully qualified names with double quotes: uploads."table_name"
4. Add LIMIT 200 at the end
5. Use proper JOIN conditions when querying multiple tables
6. Handle NULL values appropriately

Your response must be valid JSON matching the SQLResponse schema."""
    
    def _get_relevant_schema(
        self,
        question: str,
        tables: List[str],
        schema: str
    ) -> str:
        """
        Get schema context for relevant tables only.
        
        Uses simple keyword matching to identify relevant tables.
        """
        question_lower = question.lower()
        relevant_tables = []
        
        # Keyword-based table detection
        table_keywords = {
            "orders": ["order", "purchase", "buy"],
            "customers": ["customer", "buyer", "user"],
            "products": ["product", "item", "category"],
            "order_items": ["item", "product", "price"],
            "sellers": ["seller", "vendor"],
            "payments": ["payment", "pay", "transaction"],
            "reviews": ["review", "rating", "feedback"],
        }
        
        for table in tables:
            table_lower = table.lower()
            # Check if table name or keywords appear in question
            if table_lower in question_lower:
                relevant_tables.append(table)
            else:
                keywords = table_keywords.get(table_lower, [])
                if any(kw in question_lower for kw in keywords):
                    relevant_tables.append(table)
        
        # If no tables matched, include common ones
        if not relevant_tables:
            relevant_tables = ["orders", "customers", "products", "order_items"]
        
        # Get schema for relevant tables
        schema_parts = []
        for table in relevant_tables[:5]:  # Limit to 5 tables
            schema = get_table_schema(table, schema)
            schema_parts.append(schema)
        
        return "\n\n".join(schema_parts)
    
    def _validate_table_references(self, sql: str, allowed_tables: List[str]) -> bool:
        """
        Ensure SQL only references allowed tables.
        
        Prevents SQL injection attacks.
        """
        sql_lower = sql.lower()
        
        # Remove allowed table references
        for table in allowed_tables:
            sql_lower = sql_lower.replace(f'uploads."{table}"', "")
            sql_lower = sql_lower.replace(f"uploads.{table}", "")
            sql_lower = sql_lower.replace(table.lower(), "")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "from olist.",
            "join olist.",
            "from public.",
            "join public.",
        ]
        
        return not any(pattern in sql_lower for pattern in suspicious_patterns)

# Made with Bob
