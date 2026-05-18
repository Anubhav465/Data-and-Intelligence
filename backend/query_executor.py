# backend/query_executor.py

import os
import re
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing from .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"options": "-c search_path=olist"}
)

QUERY_TIMEOUT_SECONDS = 15
MAX_ROWS_LIMIT = 200


# ================================
# Internal Utilities
# ================================

def _cleanup_sql(sql_text: str) -> str:
    """Clean whitespace and newlines"""
    sql_text = sql_text.replace("\\n", "\n").strip()
    sql_text = re.sub(r"\s+\n", "\n", sql_text)
    return sql_text


def _convert_value(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def _is_safe_select(sql: str) -> bool:
    """Strict validation - only safe SELECT queries"""
    sql_lower = sql.strip().lower()

    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        return False

    if ";" in sql_lower[:-1]:
        return False

    forbidden = [
        "insert ", "update ", "delete ",
        "drop ", "alter ", "truncate ",
        "create ", "grant ", "revoke "
    ]
    for word in forbidden:
        if word in sql_lower:
            return False

    return True


def _ensure_limit(sql: str) -> str:
    """
    BULLETPROOF LIMIT HANDLING:
    - Remove ANY existing LIMIT clause (no matter the format or position)
    - Always add exactly ONE safe LIMIT 200 at the end
    - This prevents double LIMIT forever
    """
    if not sql:
        return sql

    # Remove any existing LIMIT clause (handles newlines, spaces, OFFSET, semicolon, etc.)
    sql = re.sub(r'(?is)\s+LIMIT\s+\d+(?:\s+OFFSET\s+\d+)?', '', sql)

    # Remove trailing semicolon if present
    sql = sql.rstrip(';').strip()

    # Add exactly one safe LIMIT
    sql += f"\nLIMIT {MAX_ROWS_LIMIT}"

    return sql


# ================================
# Public Execution Function
# ================================

def execute_query(sql_query: str):

    if not sql_query or not sql_query.strip():
        return {"error": "Empty SQL query."}

    sql_query = _cleanup_sql(sql_query)

    if not _is_safe_select(sql_query):
        return {"error": "Only safe SELECT queries are allowed."}

    # Apply bulletproof limit handling
    sql_query = _ensure_limit(sql_query)

    print(f"[Query Executor] FINAL SQL BEING EXECUTED:\n{sql_query}\n{'─' * 80}")

    try:
        with engine.connect() as connection:

            # Enforce timeout
            connection.execute(
                text(f"SET statement_timeout = {QUERY_TIMEOUT_SECONDS * 1000};")
            )

            result = connection.execute(text(sql_query))

            columns = list(result.keys())
            rows = [
                {col: _convert_value(val) for col, val in zip(columns, row)}
                for row in result.fetchall()
            ]

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }

    except SQLAlchemyError as e:
        return {"error": str(e)}


# ================================
# Upload Table Executor
# ================================

# Separate engine targeting the uploads schema.
_upload_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"options": "-c search_path=uploads"},
)


def execute_upload_query(sql_query: str, table_names: list[str]) -> dict:
    """
    Execute a SELECT query against one or more uploaded tables (uploads schema).

    Enforces the same safety checks as execute_query.
    table_names is used for logging; the uploads search_path handles routing.
    """
    if not sql_query or not sql_query.strip():
        return {"error": "Empty SQL query."}

    sql_query = _cleanup_sql(sql_query)

    if not _is_safe_select(sql_query):
        return {"error": "Only safe SELECT queries are allowed."}

    sql_query = _ensure_limit(sql_query)

    label = ", ".join(table_names)
    print(f"[Upload Executor][{label}] SQL:\n{sql_query}\n{'─'*80}")

    try:
        with _upload_engine.connect() as connection:
            connection.execute(
                text(f"SET statement_timeout = {QUERY_TIMEOUT_SECONDS * 1000};")
            )
            result = connection.execute(text(sql_query))
            columns = list(result.keys())
            rows = [
                {col: _convert_value(val) for col, val in zip(columns, row)}
                for row in result.fetchall()
            ]
            return {"columns": columns, "rows": rows, "row_count": len(rows)}

    except SQLAlchemyError as e:
        return {"error": str(e)}