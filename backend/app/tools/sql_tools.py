# backend/app/tools/sql_tools.py
"""
SQL-related tools using LangChain's SQLDatabaseToolkit
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize databases for both schemas
_olist_db = None
_uploads_db = None
_llm = None


def get_llm(temperature: float = 0.0):
    """Get or create LLM instance"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4-turbo-preview",  # or gpt-4o, gpt-4.1-mini
            temperature=temperature,
            api_key=OPENAI_API_KEY
        )
    return _llm


def get_olist_database():
    """Get or create SQLDatabase instance for Olist schema"""
    global _olist_db
    if _olist_db is None:
        _olist_db = SQLDatabase.from_uri(
            DATABASE_URL,
            schema="olist",
            include_tables=None,  # Include all tables
            sample_rows_in_table_info=3
        )
    return _olist_db


def get_uploads_database(table_names: Optional[List[str]] = None):
    """Get or create SQLDatabase instance for uploads schema"""
    global _uploads_db
    if _uploads_db is None:
        _uploads_db = SQLDatabase.from_uri(
            DATABASE_URL,
            schema="uploads",
            include_tables=table_names,  # Only include specified tables
            sample_rows_in_table_info=3
        )
    return _uploads_db


def create_sql_agent(schema: str = "olist", table_names: Optional[List[str]] = None):
    """
    Create a SQL agent using SQLDatabaseToolkit.
    
    This agent can:
    - List tables
    - Get table schemas
    - Generate SQL queries
    - Validate SQL
    - Execute queries
    
    Args:
        schema: "olist" or "uploads"
        table_names: For uploads schema, list of specific tables to include
    """
    llm = get_llm()
    
    if schema == "olist":
        db = get_olist_database()
    else:
        db = get_uploads_database(table_names)
    
    # Create toolkit with all SQL tools
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    
    # Enhanced system prompt for better SQL generation
    system_prompt = """You are a senior PostgreSQL analyst with expertise in e-commerce analytics.

Your task is to answer questions by generating and executing SQL queries.

STRICT RULES:
1. Always use fully qualified table names (schema.table_name)
2. Use table aliases for readability
3. Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP)
4. Add appropriate WHERE clauses to filter data
5. Use JOINs when multiple tables are needed
6. Always include LIMIT clause (max 200 rows)
7. For date comparisons, use proper timestamp casting
8. Handle NULL values appropriately

AVAILABLE TOOLS:
- sql_db_list_tables: List all available tables
- sql_db_schema: Get schema for specific tables
- sql_db_query: Execute a SQL query
- sql_db_query_checker: Validate SQL syntax

WORKFLOW:
1. First, list tables to understand what's available
2. Get schema for relevant tables
3. Generate SQL query
4. Validate the query
5. Execute and return results

Always explain your reasoning before executing queries."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=10,
        max_execution_time=60,
        handle_parsing_errors=True,
        return_intermediate_steps=True
    )


def execute_sql_with_agent(
    question: str,
    schema: str = "olist",
    table_names: Optional[List[str]] = None
) -> dict:
    """
    Execute a natural language question using the SQL agent.
    
    Returns:
        dict with keys: sql, data, explanation, intermediate_steps
    """
    try:
        agent_executor = create_sql_agent(schema, table_names)
        
        result = agent_executor.invoke({
            "input": question
        })
        
        return {
            "success": True,
            "output": result.get("output"),
            "intermediate_steps": result.get("intermediate_steps", []),
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "intermediate_steps": [],
            "error": str(e)
        }


def validate_sql_query(sql: str, schema: str = "olist") -> dict:
    """
    Validate a SQL query without executing it.
    
    Returns:
        dict with keys: valid, error_message
    """
    try:
        db = get_olist_database() if schema == "olist" else get_uploads_database()
        
        # Basic validation
        sql_lower = sql.strip().lower()
        
        if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
            return {
                "valid": False,
                "error_message": "Only SELECT queries are allowed"
            }
        
        forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "create"]
        for word in forbidden:
            if word in sql_lower:
                return {
                    "valid": False,
                    "error_message": f"Forbidden operation: {word.upper()}"
                }
        
        # Try to parse with SQLAlchemy
        from sqlalchemy import text
        text(sql)
        
        return {
            "valid": True,
            "error_message": None
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error_message": str(e)
        }


def get_table_schema(table_name: str, schema: str = "olist") -> str:
    """Get detailed schema information for a specific table"""
    try:
        db = get_olist_database() if schema == "olist" else get_uploads_database()
        return db.get_table_info([table_name])
    except Exception as e:
        return f"Error getting schema: {str(e)}"


def list_available_tables(schema: str = "olist") -> List[str]:
    """List all available tables in the specified schema"""
    try:
        db = get_olist_database() if schema == "olist" else get_uploads_database()
        return db.get_usable_table_names()
    except Exception as e:
        return []

# Made with Bob
