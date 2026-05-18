# backend/main.py
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from question_processor import process_question, process_upload_question

app = FastAPI(title="AI Analytics API — Dynamic CSV Edition")

# ── CORS ───────────────────────────────────────────────────────────────────
# Allow both local development and production frontend URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_URL,
]
# Remove duplicates
ALLOWED_ORIGINS = list(set(ALLOWED_ORIGINS))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    table_name: Optional[str] = None         # legacy single-table (kept for compat)
    table_names: Optional[List[str]] = None  # multi-table (1–5 tables)


# ── Exception handlers ─────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": 'Invalid format. Send {"question": "your question"}'},
    )


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "API running"}


# ── Existing Olist + dynamic /ask ──────────────────────────────────────────

@app.post("/ask")
def ask_question(request: QuestionRequest):
    """
    Natural-language query endpoint.

    - Without `table_name`: queries the static Olist PostgreSQL dataset.
    - With `table_name`:    queries a previously uploaded CSV table.
    """
    print(f"[API] /ask  question={request.question!r}  table={request.table_name!r}")

    # Resolve which table(s) to query
    if request.table_names:
        names = [n for n in request.table_names if n][:5]  # cap at 5
    elif request.table_name:
        names = [request.table_name]
    else:
        names = []

    if names:
        return process_upload_question(request.question, names)

    return process_question(request.question)


# ── CSV Upload ─────────────────────────────────────────────────────────────

@app.post("/upload", status_code=201)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and ingest it into PostgreSQL.

    Returns
    -------
    table_name   : unique identifier for subsequent /ask queries
    columns      : list of {name, original_name, pandas_type, pg_type}
    row_count    : number of rows successfully inserted
    preview_rows : first 5 rows of the cleaned data
    cleaning     : summary of data-quality operations performed
    """
    from file_handler import cleanup_temp_file, save_csv_upload
    from schema_inferer import infer_schema
    from data_cleaner import clean_dataframe
    from table_creator import (
        create_table,
        insert_dataframe,
        register_table_metadata,
    )
    from dynamic_retriever import register_table

    # 1. Validate & persist upload
    file_path, table_name = await save_csv_upload(file)

    try:
        # 2. Infer schema from CSV
        df, column_specs = infer_schema(file_path)

        # 3. Clean the dataframe
        clean_df, cleaning_report = clean_dataframe(df, column_specs)

        # 4. Create PostgreSQL table & bulk-insert
        create_table(table_name, column_specs)
        inserted = insert_dataframe(table_name, clean_df, column_specs)

        # 5. Persist metadata (survives restarts)
        register_table_metadata(table_name, column_specs, inserted)

        # 6. Build FAISS schema embeddings
        register_table(table_name, column_specs)

        # 7. Build preview (first 5 rows, None-safe)
        import pandas as pd
        preview_df = clean_df.head(5).where(pd.notnull(clean_df.head(5)), other=None)
        preview_rows = preview_df.to_dict(orient="records")

        return {
            "table_name": table_name,
            "columns": column_specs,
            "row_count": inserted,
            "preview_rows": preview_rows,
            "cleaning": dict(cleaning_report),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(exc)}")
    finally:
        cleanup_temp_file(file_path)


# ── Table management ───────────────────────────────────────────────────────

@app.get("/tables")
def list_tables():
    """
    List all user-uploaded tables with their column specs and row counts.
    Also ensures the in-memory FAISS registry is warm (lazy restore).
    """
    from table_creator import get_registered_tables
    from dynamic_retriever import ensure_registered

    tables = get_registered_tables()
    for t in tables:
        ensure_registered(t["table_name"], t["column_specs"])
    return {"tables": tables}


@app.get("/tables/{table_name}")
def get_table_info(table_name: str):
    """Return metadata for a single uploaded table."""
    from table_creator import get_table_metadata

    meta = get_table_metadata(table_name)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")
    return meta


@app.delete("/tables/{table_name}", status_code=200)
def delete_table(table_name: str):
    """
    Drop an uploaded table from PostgreSQL and remove its schema index.
    """
    from table_creator import drop_table, get_table_metadata
    from dynamic_retriever import deregister_table

    if not get_table_metadata(table_name):
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")

    drop_table(table_name)
    deregister_table(table_name)
    return {"deleted": table_name}
