# backend/app/api/routes.py
"""
FastAPI routes for Neural Analytics 3.0 with LangChain/LangGraph
"""
import os
from typing import List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.graph import get_workflow

# Import existing modules for upload functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from file_handler import cleanup_temp_file, save_csv_upload
from schema_inferer import infer_schema
from data_cleaner import clean_dataframe
from table_creator import (
    create_table,
    insert_dataframe,
    register_table_metadata,
    get_registered_tables,
    get_table_metadata,
    drop_table,
)
from dynamic_retriever import register_table, deregister_table, ensure_registered

app = FastAPI(title="Neural Analytics 3.0 - LangChain Edition")

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = list(set([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_URL,
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== REQUEST/RESPONSE MODELS ==========

class QuestionRequest(BaseModel):
    question: str
    table_name: Optional[str] = None
    table_names: Optional[List[str]] = None


# ========== HEALTH CHECK ==========

@app.get("/")
def health_check():
    return {
        "status": "Neural Analytics 3.0 running",
        "version": "3.0.0",
        "powered_by": "LangChain + LangGraph"
    }


# ========== MAIN QUERY ENDPOINT ==========

@app.post("/ask")
def ask_question(request: QuestionRequest):
    """
    Natural language query endpoint powered by LangChain/LangGraph.
    
    - Without table_name: queries the Olist PostgreSQL dataset
    - With table_name: queries a previously uploaded CSV table
    - Supports multi-table queries (up to 5 tables)
    """
    print(f"[API] /ask question={request.question!r} tables={request.table_names or request.table_name}")
    
    # Resolve which table(s) to query
    if request.table_names:
        table_names = [n for n in request.table_names if n][:5]
    elif request.table_name:
        table_names = [request.table_name]
    else:
        table_names = None
    
    try:
        # Get the LangGraph workflow
        workflow = get_workflow()
        
        # Process the question through the workflow
        result = workflow.process_question(
            question=request.question,
            table_names=table_names
        )
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


# ========== CSV UPLOAD ==========

@app.post("/upload", status_code=201)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and ingest it into PostgreSQL.
    
    Returns table metadata including schema, row count, and preview.
    """
    file_path, table_name = await save_csv_upload(file)
    
    try:
        # Infer schema
        df, column_specs = infer_schema(file_path)
        
        # Clean data
        clean_df, cleaning_report = clean_dataframe(df, column_specs)
        
        # Create PostgreSQL table
        create_table(table_name, column_specs)
        inserted = insert_dataframe(table_name, clean_df, column_specs)
        
        # Register metadata
        register_table_metadata(table_name, column_specs, inserted)
        
        # Build FAISS embeddings
        register_table(table_name, column_specs)
        
        # Build preview
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
        raise HTTPException(
            status_code=500,
            detail=f"Upload processing failed: {str(exc)}"
        )
    finally:
        cleanup_temp_file(file_path)


# ========== TABLE MANAGEMENT ==========

@app.get("/tables")
def list_tables():
    """List all user-uploaded tables with metadata"""
    tables = get_registered_tables()
    for t in tables:
        ensure_registered(t["table_name"], t["column_specs"])
    return {"tables": tables}


@app.get("/tables/{table_name}")
def get_table_info(table_name: str):
    """Get metadata for a single uploaded table"""
    meta = get_table_metadata(table_name)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found."
        )
    return meta


@app.delete("/tables/{table_name}", status_code=200)
def delete_table(table_name: str):
    """Drop an uploaded table and remove its schema index"""
    if not get_table_metadata(table_name):
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found."
        )
    
    drop_table(table_name)
    deregister_table(table_name)
    return {"deleted": table_name}


# ========== LANGSMITH TRACING INFO ==========

@app.get("/tracing")
def tracing_info():
    """Get LangSmith tracing configuration"""
    langsmith_enabled = bool(os.getenv("LANGCHAIN_TRACING_V2"))
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "neural-analytics")
    
    return {
        "tracing_enabled": langsmith_enabled,
        "project": langsmith_project,
        "endpoint": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
    }

# Made with Bob
