# backend/sql_generator.py

import os
import re
import requests
from dotenv import load_dotenv
from schema_extractor import extract_schema
from dynamic_retriever import get_schema_context, retrieve_relevant_chunks

load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_URL = "https://api.cohere.com/v2/chat"

HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json"
}


# ==========================================
# ROBUST SQL EXTRACTION
# ==========================================

def extract_sql(raw_output: str) -> str:
    if not raw_output:
        return ""

    raw = raw_output.strip()

    blocks = re.findall(r'```(?:sql|postgresql)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if blocks:
        return max(blocks, key=len).strip()

    match = re.search(r'(WITH|SELECT)[\s\S]*', raw, re.IGNORECASE)
    if match:
        return match.group(0).strip()

    return raw


# ==========================================
# BULLETPROOF CLEANER
# ==========================================

def clean_sql_output(raw_sql: str) -> str:
    if not raw_sql:
        return ""

    sql = raw_sql.strip()

    if "```" in sql:
        match = re.search(r'```(?:sql|postgresql)?\s*(.*?)\s*```', sql, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()

    sql = sql.rstrip(';').strip()

    # Remove any existing LIMIT
    sql = re.sub(r'(?is)\s+LIMIT\s+\d+(?:\s+OFFSET\s+\d+)?', '', sql)

    sql = sql.strip() + "\nLIMIT 200"
    return sql


# ==========================================
# SQL SAFETY VALIDATION
# ==========================================

def validate_sql(sql: str):
    if not sql:
        raise ValueError("Empty SQL generated.")

    lowered = sql.strip().lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only safe SELECT queries are allowed.")

    forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create "]
    if any(word in lowered for word in forbidden):
        raise ValueError("Destructive queries are not allowed.")

    if sql.strip().count(';') > 1:
        raise ValueError("Multiple SQL statements are not allowed.")

    return True


# ==========================================
# MAIN SQL GENERATOR - STRONG CATEGORY FIX
# ==========================================

def generate_sql(user_query: str, chat_history=None):
    if chat_history is None:
        chat_history = []

    schema_context = extract_schema()

    system_prompt = f"""You are a senior PostgreSQL analyst for Olist Brazilian e-commerce.

STRICT RULES — VIOLATE = INVALID:
- Return ONLY raw SQL. No explanations, no markdown, no ```, no comments.
- ALWAYS start with SELECT or WITH.
- ALWAYS use fully qualified names: olist.orders, olist.products, olist.order_items etc.
- ALWAYS alias tables (o, p, oi, c...).
- ALWAYS qualify joins (oi.product_id = p.product_id).

CRITICAL FOR PRODUCT CATEGORIES:
- There is NO table called product_category_name_translation in the database.
- NEVER join or mention any translation table.
- Product category names (in Portuguese) are in olist.products.product_category_name.
- To get categories by sales you MUST join like this:
  FROM olist.order_items oi
  JOIN olist.products p ON oi.product_id = p.product_id
- Use p.product_category_name in SELECT and GROUP BY.
- Translation to English happens in Python AFTER the query.

Database Schema:
{schema_context}

Examples:

User: top 5 product categories by sales
Assistant:
SELECT p.product_category_name,
       SUM(oi.price) AS total_sales
FROM olist.order_items oi
JOIN olist.products p ON oi.product_id = p.product_id
GROUP BY p.product_category_name
ORDER BY total_sales DESC

User: highest selling product in 2018
Assistant:
SELECT p.product_category_name, 
       SUM(oi.price) AS total_sales
FROM olist.order_items oi
JOIN olist.products p ON oi.product_id = p.product_id
JOIN olist.orders o ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp BETWEEN '2018-01-01' AND '2018-12-31'
GROUP BY p.product_category_name
ORDER BY total_sales DESC

Now generate SQL for the user question below. Return ONLY the SQL."""

    messages = [{"role": "system", "content": system_prompt}]

    for turn in chat_history[-4:]:
        messages.append({"role": "user", "content": turn["query"]})
        messages.append({"role": "assistant", "content": turn["sql"]})

    messages.append({"role": "user", "content": user_query})

    payload = {
        "model": "command-r-08-2024",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 800
    }

    try:
        print(f"\n[SQL Generator] Processing query: {user_query[:150]}...")

        response = requests.post(COHERE_URL, headers=HEADERS, json=payload, timeout=35)

        if response.status_code >= 400:
            raise RuntimeError(f"Cohere API error {response.status_code}: {response.text[:400]}")

        data = response.json()
        blocks = data.get("message", {}).get("content", [])
        raw_output = next((b.get("text") for b in blocks if b.get("type") == "text"), "")

        if not raw_output:
            raise RuntimeError("Model returned empty response")

        print(f"[SQL Generator] RAW OUTPUT FROM MODEL:\n{raw_output}\n{'─' * 90}")

        extracted = extract_sql(raw_output)
        final_sql = clean_sql_output(extracted)

        print(f"[SQL Generator] FINAL CLEAN SQL:\n{final_sql}\n{'─' * 90}")

        validate_sql(final_sql)
        return final_sql

    except Exception as e:
        print(f"[SQL Generator ERROR] {str(e)}")
        raise RuntimeError(f"SQL generation failed: {str(e)}")


# ==========================================
# DYNAMIC TABLE SQL GENERATOR
# ==========================================

def generate_sql_for_upload(user_query: str, table_names: list[str]) -> str:
    """
    Generate a SELECT-only SQL query for one or more user-uploaded tables.

    Parameters
    ----------
    user_query   : natural-language question from the user
    table_names  : list of uploads.<table_name> identifiers (1–5 tables)

    Returns
    -------
    Cleaned, validated, LIMIT-appended SQL string.
    """
    is_multi = len(table_names) > 1

    # Build schema context.
    # For a single table: full context + top relevant FAISS chunks for precision.
    # For multiple tables: full context only (no duplicated chunks) to keep
    # the prompt small and avoid Cohere timeouts.
    schema_sections = []
    for tn in table_names:
        full_ctx = get_schema_context(tn)
        if is_multi:
            schema_sections.append(f'TABLE: uploads."{tn}"\n{full_ctx}')
        else:
            chunks = retrieve_relevant_chunks(tn, user_query, top_k=4)
            schema_sections.append(
                f'TABLE: uploads."{tn}"\n{full_ctx}\n\nRelevant columns:\n' + "\n".join(chunks[1:])
            )
    combined_schema = "\n\n" + ("─" * 60 + "\n\n").join(schema_sections)

    # Build allowed-tables instruction
    allowed_refs = "\n".join(f'  - uploads."{tn}"' for tn in table_names)
    join_note = (
        "- You MAY JOIN these tables when the question requires it.\n"
        if is_multi else ""
    )
    single_note = (
        ""
        if is_multi
        else f'- ONLY query the single table uploads."{table_names[0]}" — no other tables.\n'
    )

    system_prompt = f"""You are a senior PostgreSQL analyst. The user uploaded CSV file(s) loaded into the table(s) below.

STRICT RULES — VIOLATE = INVALID:
- Return ONLY raw SQL. No explanations, no markdown, no ```, no comments.
- ALWAYS start with SELECT or WITH.
- ONLY use these exact tables (fully qualified):
{allowed_refs}
{single_note}{join_note}- Use column names exactly as shown in the schema.
- Do NOT add LIMIT yourself.

Schemas:
{combined_schema}

Generate SQL for the user question below. Return ONLY the SQL."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]

    payload = {
        "model": "command-r-08-2024",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 700,
    }

    label = f"[{len(table_names)} table(s)]"
    print(f"[SQL Generator][upload]{label} Query: {user_query[:120]}...")

    last_error: Exception | None = None
    for attempt in (1, 2):          # one retry on timeout
        try:
            response = requests.post(COHERE_URL, headers=HEADERS, json=payload, timeout=60)

            if response.status_code >= 400:
                raise RuntimeError(
                    f"Cohere API error {response.status_code}: {response.text[:400]}"
                )

            data = response.json()
            blocks = data.get("message", {}).get("content", [])
            raw_output = next(
                (b.get("text") for b in blocks if b.get("type") == "text"), ""
            )

            if not raw_output:
                raise RuntimeError("Model returned empty response")

            print(f"[SQL Generator][upload] RAW:\n{raw_output}\n{'─'*80}")

            extracted = extract_sql(raw_output)
            final_sql = clean_sql_output(extracted)

            print(f"[SQL Generator][upload] CLEAN:\n{final_sql}\n{'─'*80}")

            validate_sql(final_sql)
            _assert_allowed_tables(final_sql, table_names)

            return final_sql

        except requests.exceptions.Timeout as e:
            last_error = e
            print(f"[SQL Generator][upload] Timeout on attempt {attempt}/2 — {'retrying' if attempt == 1 else 'giving up'}")
        except Exception as e:
            print(f"[SQL Generator][upload] ERROR: {str(e)}")
            raise RuntimeError(f"SQL generation failed for upload table(s): {str(e)}")

    raise RuntimeError(
        f"SQL generation timed out after 2 attempts (Cohere took > 60 s). "
        "Try asking a simpler question or query fewer tables at once."
    )


def _assert_allowed_tables(sql: str, table_names: list[str]) -> None:
    """
    Raise ValueError if the generated SQL references any table not in
    table_names.  Prevents prompt-injection attacks targeting other schemas.
    Accepts a list so multi-table JOIN queries are permitted.
    """
    lowered = sql.lower()
    scrubbed = lowered
    for tn in table_names:
        scrubbed = scrubbed.replace(f'uploads."{tn}"', "")
        scrubbed = scrubbed.replace(f"uploads.{tn}", "")
        scrubbed = scrubbed.replace(tn.lower(), "")

    # SQL keywords that can legally follow FROM/JOIN — never table names
    _SQL_KEYWORDS = {
        "", "lateral", "unnest", "select", "where", "limit", "order", "group",
        "by", "having", "union", "intersect", "except", "with", "as", "on",
        "and", "or", "not", "null", "true", "false", "case", "when", "then",
        "else", "end", "in", "between", "like", "is", "distinct", "all",
        "insert", "update", "delete", "create", "drop", "alter", "set",
        "returning", "values", "into", "from", "join", "inner", "outer",
        "left", "right", "full", "cross", "natural", "using", "over",
        "partition", "window", "filter", "within", "rows", "range",
    }

    suspicious = re.findall(r"\bfrom\s+(\w+\.?\w+)", scrubbed)
    suspicious += re.findall(r"\bjoin\s+(\w+\.?\w+)", scrubbed)
    suspicious = [s for s in suspicious if s not in _SQL_KEYWORDS]

    if suspicious:
        raise ValueError(
            f"Generated SQL references unauthorised tables: {suspicious}"
        )