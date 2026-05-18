# backend/table_creator.py
"""
PostgreSQL table management for user-uploaded datasets.

All uploaded tables live in the `uploads` schema, isolated from the
production `olist` schema.  A metadata registry table persists column
specs so they survive server restarts.
"""
from __future__ import annotations

import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from schema_inferer import ColumnSpec

load_dotenv()

_DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if not _DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment.")

UPLOAD_SCHEMA = "uploads"

# Engine without a forced search_path so fully-qualified names always work.
_engine = create_engine(
    _DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# ── Bootstrap ──────────────────────────────────────────────────────────────

def _ensure_upload_schema() -> None:
    """Create the uploads schema and metadata registry if they don't exist."""
    with _engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {UPLOAD_SCHEMA}"))
        conn.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS {UPLOAD_SCHEMA}._table_registry (
                    table_name   TEXT PRIMARY KEY,
                    column_specs JSONB   NOT NULL,
                    row_count    INTEGER NOT NULL DEFAULT 0,
                    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
        )


# ── Public API ─────────────────────────────────────────────────────────────

def create_table(table_name: str, column_specs: list[ColumnSpec]) -> None:
    """
    Create uploads.<table_name> from *column_specs*.

    Drops any pre-existing table with the same name first to ensure
    this operation is idempotent (safe to call on re-upload).
    """
    _ensure_upload_schema()

    col_defs = ",\n    ".join(
        f'"{spec["name"]}"  {spec["pg_type"]}' for spec in column_specs
    )
    with _engine.begin() as conn:
        conn.execute(
            text(f'DROP TABLE IF EXISTS {UPLOAD_SCHEMA}."{table_name}" CASCADE')
        )
        conn.execute(
            text(f"""
                CREATE TABLE {UPLOAD_SCHEMA}."{table_name}" (
                    _row_id SERIAL PRIMARY KEY,
                    {col_defs}
                )
            """)
        )


def insert_dataframe(
    table_name: str,
    df: pd.DataFrame,
    column_specs: list[ColumnSpec],
) -> int:
    """
    Bulk-insert *df* into uploads.<table_name>.

    Uses pandas to_sql with method='multi' for efficient batch inserts.
    Returns the number of rows actually inserted.
    """
    # Only include columns declared in the schema (drop any extras / _row_id)
    declared_cols = [spec["name"] for spec in column_specs]
    insert_df = df[[c for c in declared_cols if c in df.columns]].copy()

    # pandas NaN / NaT → Python None → SQL NULL
    insert_df = insert_df.where(pd.notnull(insert_df), other=None)

    insert_df.to_sql(
        name=table_name,
        con=_engine,
        schema=UPLOAD_SCHEMA,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    return len(insert_df)


def register_table_metadata(
    table_name: str,
    column_specs: list[ColumnSpec],
    row_count: int,
) -> None:
    """
    Persist column specs in the metadata registry so they survive restarts.
    """
    _ensure_upload_schema()
    with _engine.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {UPLOAD_SCHEMA}._table_registry
                    (table_name, column_specs, row_count)
                VALUES (:name, CAST(:specs AS jsonb), :rows)
                ON CONFLICT (table_name) DO UPDATE
                    SET column_specs = EXCLUDED.column_specs,
                        row_count    = EXCLUDED.row_count,
                        created_at   = NOW()
            """),
            {"name": table_name, "specs": json.dumps(column_specs), "rows": row_count},
        )


def get_registered_tables() -> list[dict]:
    """
    Return all entries from the metadata registry.

    Each entry: {table_name, column_specs, row_count, created_at}
    """
    _ensure_upload_schema()
    with _engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT table_name, column_specs, row_count, created_at
                FROM {UPLOAD_SCHEMA}._table_registry
                ORDER BY created_at DESC
            """)
        ).fetchall()
    return [
        {
            "table_name": r[0],
            "column_specs": r[1] if isinstance(r[1], list) else json.loads(r[1]),
            "row_count": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


def get_table_metadata(table_name: str) -> dict | None:
    """
    Fetch metadata for a single table. Returns None if not found.
    """
    _ensure_upload_schema()
    with _engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT table_name, column_specs, row_count, created_at
                FROM {UPLOAD_SCHEMA}._table_registry
                WHERE table_name = :name
            """),
            {"name": table_name},
        ).fetchone()
    if not row:
        return None
    return {
        "table_name": row[0],
        "column_specs": row[1] if isinstance(row[1], list) else json.loads(row[1]),
        "row_count": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
    }


def drop_table(table_name: str) -> None:
    """
    Drop the table and remove it from the metadata registry.
    """
    with _engine.begin() as conn:
        conn.execute(
            text(f'DROP TABLE IF EXISTS {UPLOAD_SCHEMA}."{table_name}" CASCADE')
        )
        conn.execute(
            text(f"""
                DELETE FROM {UPLOAD_SCHEMA}._table_registry
                WHERE table_name = :name
            """),
            {"name": table_name},
        )
