# backend/dynamic_retriever.py
"""
Per-upload FAISS schema embeddings and schema context retrieval.

Each uploaded table gets its own FAISS index built from per-column
schema chunks.  The registry is in-memory (rebuilt from PostgreSQL on
demand) so it survives server restarts transparently.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import cohere
import faiss
import numpy as np
from dotenv import load_dotenv

from schema_inferer import ColumnSpec

load_dotenv()

_co = cohere.Client(os.getenv("COHERE_API_KEY", ""))
_EMBED_MODEL = "embed-english-v3.0"
_EMBED_DIM = 1024          # embed-english-v3.0 output dimension
UPLOAD_SCHEMA = "uploads"  # must match table_creator.UPLOAD_SCHEMA


@dataclass
class _TableIndex:
    index: faiss.IndexFlatL2 | None   # None when embedding unavailable
    chunks: list[str]                 # text chunks (first = full-table summary)
    full_context: str                 # ready-to-use prompt context string
    column_specs: list[ColumnSpec]    # retained for schema reconstruction


# In-memory registry: table_name → _TableIndex
_registry: dict[str, _TableIndex] = {}


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_chunks(table_name: str, column_specs: list[ColumnSpec]) -> list[str]:
    """
    Produce a list of text chunks for embedding:
    - chunk[0]: full table summary  (used as fallback full context)
    - chunk[1..n]: one chunk per column  (fine-grained retrieval)
    """
    col_lines = "\n".join(
        f"  {s['name']} ({s['pg_type']})  [original header: \"{s['original_name']}\"]"
        for s in column_specs
    )
    full = (
        f"Table: {UPLOAD_SCHEMA}.\"{table_name}\"\n"
        f"Columns:\n{col_lines}"
    )
    per_col = [
        (
            f"Table: {table_name} | "
            f"Column: {s['name']} | "
            f"PostgreSQL type: {s['pg_type']} | "
            f"Original header: \"{s['original_name']}\""
        )
        for s in column_specs
    ]
    return [full] + per_col


def _embed(texts: list[str], input_type: str = "search_document") -> np.ndarray:
    resp = _co.embed(texts=texts, model=_EMBED_MODEL, input_type=input_type)
    return np.array(resp.embeddings, dtype="float32")


def _build_index(chunks: list[str]) -> faiss.IndexFlatL2 | None:
    """Build a FAISS L2 index from *chunks*. Returns None on failure."""
    try:
        vectors = _embed(chunks, "search_document")
        idx = faiss.IndexFlatL2(_EMBED_DIM)
        idx.add(vectors)
        return idx
    except Exception as exc:
        print(f"[DynamicRetriever] FAISS index build failed: {exc}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────

def register_table(table_name: str, column_specs: list[ColumnSpec]) -> None:
    """
    Embed the schema for *table_name* and store in the in-memory registry.

    Should be called immediately after the PostgreSQL table is created.
    Silently falls back to a text-only context if Cohere is unreachable.
    """
    chunks = _build_chunks(table_name, column_specs)
    idx = _build_index(chunks)
    _registry[table_name] = _TableIndex(
        index=idx,
        chunks=chunks,
        full_context=chunks[0],
        column_specs=column_specs,
    )
    print(f"[DynamicRetriever] Registered schema for '{table_name}' ({len(column_specs)} cols)")


def ensure_registered(table_name: str, column_specs: list[ColumnSpec]) -> None:
    """
    Register *table_name* only if it is not already in the registry.
    Used to lazily restore registrations after a server restart.
    """
    if table_name not in _registry:
        register_table(table_name, column_specs)


def get_schema_context(table_name: str) -> str:
    """
    Return the full schema context string suitable for injection into
    the SQL-generation prompt.
    """
    entry = _registry.get(table_name)
    if entry is None:
        return f'Table: {UPLOAD_SCHEMA}."{table_name}" (schema not indexed)'
    return entry.full_context


def retrieve_relevant_chunks(
    table_name: str,
    query: str,
    top_k: int = 6,
) -> list[str]:
    """
    Retrieve the most relevant schema chunks for *query* using FAISS
    semantic search.  Falls back to the full context on failure.
    """
    entry = _registry.get(table_name)
    if entry is None or entry.index is None:
        return [get_schema_context(table_name)]

    try:
        q_vec = _embed([query], "search_query")
        k = min(top_k, len(entry.chunks))
        _dists, idxs = entry.index.search(q_vec, k)
        return [entry.chunks[i] for i in idxs[0] if 0 <= i < len(entry.chunks)]
    except Exception:
        return [entry.full_context]


def deregister_table(table_name: str) -> None:
    """Remove schema embeddings for *table_name* from the registry."""
    _registry.pop(table_name, None)


def list_registered_tables() -> list[str]:
    """Return all table names currently held in memory."""
    return list(_registry.keys())
