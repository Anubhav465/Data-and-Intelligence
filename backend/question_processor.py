# backend/question_processor.py

import json
import time
import os
from datetime import datetime, date
from decimal import Decimal
from fastapi import HTTPException
from dotenv import load_dotenv
from tabulate import tabulate
import requests

from category_translator import translate_categories   # ← your translator
from analytics_queries import (
    avg_late_days_query,
    pct_late_query,
    avg_abs_delay_query
)
from sql_generator import generate_sql, generate_sql_for_upload, clean_sql_output
from query_executor import execute_query, execute_upload_query
from chart_generator import generate_chart_spec
from dynamic_retriever import get_schema_context

load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_URL = "https://api.cohere.com/v2/chat"

HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}


# ==========================================
# JSON Serializer (unchanged)
# ==========================================

def make_json_serializable(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


# ==========================================
# KPI Router (unchanged)
# ==========================================

def route_question(question: str):
    q = question.lower()

    if "percentage" in q and "late" in q:
        return pct_late_query(), "Percentage of late deliveries by state.", "kpi_router"

    if "average late" in q or "avg late" in q:
        return avg_late_days_query(), "Average late days by state.", "kpi_router"

    if "absolute delay" in q:
        return avg_abs_delay_query(), "Average absolute delivery delay by state.", "kpi_router"

    return None, None, None


# ==========================================
# ROBUST AUTO-FIX (unchanged)
# ==========================================

def attempt_sql_fix(original_sql, error_message):
    print(f"[Auto Fix] Original failing SQL:\n{original_sql}")
    print(f"[Auto Fix] Error: {error_message}")

    fix_prompt = f"""
The following PostgreSQL query failed:

Error:
{error_message}

Original SQL:
{original_sql}

Fix it and return ONLY the raw corrected SQL.
- Do NOT add LIMIT yourself.
- Use olist.table_name and aliases.
"""

    payload = {
        "model": "command-r-08-2024",
        "messages": [
            {"role": "system", "content": "You are an expert PostgreSQL query fixer. Return ONLY fixed raw SQL."},
            {"role": "user", "content": fix_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 700
    }

    try:
        r = requests.post(COHERE_URL, headers=HEADERS, json=payload, timeout=25)
        if r.status_code >= 400:
            return None

        data = r.json()
        blocks = data.get("message", {}).get("content", [])

        for block in blocks:
            if block.get("type") == "text":
                fixed = block.get("text", "").strip()
                print(f"[Auto Fix] Raw from Cohere:\n{fixed}")
                return clean_sql_output(fixed)

        return None

    except:
        return None


# ==========================================
# EXECUTIVE SUMMARY (unchanged - already perfect)
# ==========================================

def generate_summary(question, rows):
    if not rows:
        return "No data available for this query."

    sample_rows = rows[:15]

    prompt = f"""Question: {question}

Data sample (first 15 rows):
{json.dumps(sample_rows, indent=2, default=make_json_serializable)}

Return EXACTLY 3 concise bullet points.
- Each bullet must be one short sentence.
- Use real numbers and exact insights from the data.
- No extra text, no introduction, no markdown."""

    payload = {
        "model": "command-r-08-2024",
        "messages": [
            {"role": "system", "content": "You are an expert business analyst. Always respond with exactly 3 bullet points. No other text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 300
    }

    try:
        print("[Summary Generator] Sending request to Cohere...")
        r = requests.post(COHERE_URL, headers=HEADERS, json=payload, timeout=20)

        if r.status_code >= 400:
            return "Summary generation failed."

        data = r.json()
        blocks = data.get("message", {}).get("content", [])

        full_text = ""
        for block in blocks:
            if block.get("type") == "text":
                full_text += block.get("text", "") + "\n"

        summary = full_text.strip()
        lines = [line.strip() for line in summary.split("\n") if line.strip()]
        bullets = [line for line in lines if line.startswith(("•", "-", "*"))]

        final_summary = "\n".join(bullets[:3]) if len(bullets) >= 3 else summary
        print(f"[Summary Generator] SUCCESS:\n{final_summary}")
        return final_summary

    except Exception as e:
        print(f"[Summary Generator] Error: {str(e)}")
        return "Summary unavailable."


# ==========================================
# Main Processor - TRANSLATION INTEGRATED
# ==========================================

def process_question(question: str):

    start_time = time.time()

    print("\n[Processor] Routing question...")

    sql, explanation, source = route_question(question)

    if not sql:
        print("[Processor] No router match → calling LLM SQL generator...")
        try:
            sql = generate_sql(question)
            explanation = "LLM-generated SQL."
            source = "llm"
        except Exception as e:
            print(f"[Processor] SQL Generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Could not generate SQL: {str(e)}")

    sql = clean_sql_output(sql)

    print("[Processor] Executing SQL...")
    execution = execute_query(sql)

    if "error" in execution:
        print(f"Execution failed with error: {execution['error']}")
        print("Attempting auto-fix...")
        fixed_sql = attempt_sql_fix(sql, execution["error"])
        if fixed_sql:
            fixed_sql = clean_sql_output(fixed_sql)
            execution = execute_query(fixed_sql)
            if "error" not in execution:
                sql = fixed_sql
                explanation += " (auto-corrected)"
            else:
                raise HTTPException(status_code=400, detail=execution["error"])
        else:
            raise HTTPException(status_code=400, detail=execution["error"])

    rows = execution["rows"]
    columns = execution.get("columns", [])

    # ====================== CATEGORY TRANSLATION ======================
    print("[Processor] Applying Portuguese → English category translation...")
    translated_rows = translate_categories(rows, columns)
    execution["rows"] = translated_rows
    rows = translated_rows
    # ================================================================

    table_output = tabulate(rows, headers="keys", tablefmt="pretty")

    chart = generate_chart_spec(execution, question)
    summary = generate_summary(question, rows)

    execution_time_ms = round((time.time() - start_time) * 1000, 2)

    meta = {
        "execution_time_ms": execution_time_ms,
        "source": source,
        "row_count": execution["row_count"],
        "chart_available": chart is not None
    }

    return {
        "question": question,
        "sql": sql,
        "explanation": explanation,
        "table": table_output,
        "data": execution,
        "chart_spec": chart,
        "summary": summary,
        "meta": meta
    }


# ==========================================
# Upload Table Auto-Fix
# ==========================================

def _attempt_upload_fix(original_sql: str, error_message: str, table_names: list[str]) -> str | None:
    """Auto-correct a failing upload-table SQL query using the LLM."""
    # Build combined schema context for all involved tables
    schema_parts = [get_schema_context(tn) for tn in table_names]
    schema_context = "\n\n".join(
        f'uploads."{tn}":\n{ctx}' for tn, ctx in zip(table_names, schema_parts)
    )
    allowed = ", ".join(f'uploads."{tn}"' for tn in table_names)

    fix_prompt = f"""
The following PostgreSQL query failed:

Error:
{error_message}

Original SQL:
{original_sql}

Allowed table(s): {allowed}

Schemas:
{schema_context}

Fix the query and return ONLY the corrected raw SQL.
- Use FULLY QUALIFIED table names from the allowed list above.
- Do NOT add LIMIT yourself.
- Do NOT query any other tables.
"""
    payload = {
        "model": "command-r-08-2024",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert PostgreSQL query fixer. Return ONLY raw SQL.",
            },
            {"role": "user", "content": fix_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 600,
    }
    try:
        r = requests.post(COHERE_URL, headers=HEADERS, json=payload, timeout=25)
        if r.status_code >= 400:
            return None
        blocks = r.json().get("message", {}).get("content", [])
        for block in blocks:
            if block.get("type") == "text":
                return clean_sql_output(block.get("text", "").strip())
        return None
    except Exception:
        return None


# ==========================================
# Upload Table Query Processor
# ==========================================

def process_upload_question(question: str, table_names: list[str]) -> dict:
    """
    Full NL→SQL→execute→summarise pipeline for one or more user-uploaded tables.

    Parameters
    ----------
    question    : natural-language question from the user
    table_names : list of uploads.<table_name> identifiers (1–5 tables)
    """
    start_time = time.time()

    print(f"\n[UploadProcessor] '{question}' → tables {table_names}")

    # ── Generate SQL ──────────────────────────────────────────────────────
    try:
        sql = generate_sql_for_upload(question, table_names)
        sql = clean_sql_output(sql)
        explanation = "LLM-generated SQL for uploaded table(s)."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL generation failed: {str(e)}")

    # ── Execute ───────────────────────────────────────────────────────────
    execution = execute_upload_query(sql, table_names)

    if "error" in execution:
        print(f"[UploadProcessor] Execution failed: {execution['error']} — attempting auto-fix")
        fixed_sql = _attempt_upload_fix(sql, execution["error"], table_names)
        if fixed_sql:
            fixed_sql = clean_sql_output(fixed_sql)
            execution = execute_upload_query(fixed_sql, table_names)
            if "error" not in execution:
                sql = fixed_sql
                explanation += " (auto-corrected)"
            else:
                raise HTTPException(status_code=400, detail=execution["error"])
        else:
            raise HTTPException(status_code=400, detail=execution["error"])

    rows = execution["rows"]
    table_output = tabulate(rows, headers="keys", tablefmt="pretty")
    chart = generate_chart_spec(execution, question)
    summary = generate_summary(question, rows)
    execution_time_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "question": question,
        "table_names": table_names,
        "sql": sql,
        "explanation": explanation,
        "table": table_output,
        "data": execution,
        "chart_spec": chart,
        "summary": summary,
        "meta": {
            "execution_time_ms": execution_time_ms,
            "source": "llm_upload",
            "row_count": execution["row_count"],
            "chart_available": chart is not None,
        },
    }