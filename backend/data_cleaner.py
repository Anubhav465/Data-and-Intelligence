# backend/data_cleaner.py
"""
DataFrame sanitisation before PostgreSQL bulk insertion.

Cleaning pipeline (in order):
  1. Null-string normalisation  – common null-like strings → None
  2. Type coercion              – re-cast each column to its inferred PG type
  3. Duplicate removal          – drop exact duplicate rows
  4. LLM suggestions (optional) – Cohere-powered data-quality hints
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from schema_inferer import ColumnSpec

load_dotenv()

_COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
_COHERE_URL = "https://api.cohere.com/v2/chat"
_COHERE_HEADERS = {
    "Authorization": f"Bearer {_COHERE_API_KEY}",
    "Content-Type": "application/json",
}

# Strings that represent a missing value but aren't NaN
_NULL_STRINGS: frozenset[str] = frozenset(
    {"n/a", "na", "nan", "null", "none", "nil", "", "-", "?", "–", "—", "unknown"}
)


# ── Internal helpers ───────────────────────────────────────────────────────

def _replace_null_strings(series: pd.Series) -> pd.Series:
    """Map common null-like string representations to None (→ SQL NULL)."""
    if series.dtype != object:
        return series
    return series.apply(
        lambda v: None
        if isinstance(v, str) and v.strip().lower() in _NULL_STRINGS
        else v
    )


def _coerce_column(series: pd.Series, pg_type: str) -> tuple[pd.Series, int]:
    """
    Attempt to cast *series* to the target PG type.

    Returns (coerced_series, failure_count).
    """
    before_nulls = series.isna().sum()

    if "INT" in pg_type:
        coerced = pd.to_numeric(series, errors="coerce").astype("Int64")
    elif pg_type in ("REAL", "DOUBLE PRECISION"):
        coerced = pd.to_numeric(series, errors="coerce")
    elif pg_type == "BOOLEAN":
        true_vals = {"true", "1", "yes", "t", "y"}
        false_vals = {"false", "0", "no", "f", "n"}
        coerced = series.apply(
            lambda v: True if str(v).strip().lower() in true_vals
            else False if str(v).strip().lower() in false_vals
            else None
        )
    elif pg_type == "TIMESTAMP":
        coerced = pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
    else:
        return series, 0

    failure_count = int(coerced.isna().sum() - before_nulls)
    return coerced, max(failure_count, 0)


# ── Public API ─────────────────────────────────────────────────────────────

class CleaningReport(dict):
    """
    Dict subclass for JSON-serialisable cleaning metadata.

    Keys
    ----
    null_strings_replaced    : int
    rows_dropped_duplicates  : int
    type_coercion_failures   : dict[col_name, failure_count]
    total_rows_after         : int
    llm_suggestions          : list[str]  (empty when skip_llm=True)
    """


def clean_dataframe(
    df: pd.DataFrame,
    column_specs: list[ColumnSpec],
    *,
    skip_llm: bool = False,
) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Sanitise *df* in-place (operates on a copy) and return a cleaning report.

    Parameters
    ----------
    df            : DataFrame produced by schema_inferer.infer_schema
    column_specs  : column metadata from schema_inferer.infer_schema
    skip_llm      : when True, skip the Cohere cleaning-suggestion step
    """
    df = df.copy()
    report = CleaningReport(
        null_strings_replaced=0,
        rows_dropped_duplicates=0,
        type_coercion_failures={},
        total_rows_after=0,
        llm_suggestions=[],
    )
    pg_type_map = {spec["name"]: spec["pg_type"] for spec in column_specs}

    # ── 1. Null-string normalisation ───────────────────────────────────────
    null_count = 0
    for col in df.select_dtypes(include="object").columns:
        before = int(df[col].isna().sum())
        df[col] = _replace_null_strings(df[col])
        after = int(df[col].isna().sum())
        null_count += after - before
    report["null_strings_replaced"] = null_count

    # ── 2. Type coercion ───────────────────────────────────────────────────
    for col in df.columns:
        pg_type = pg_type_map.get(col, "TEXT")
        try:
            coerced, failures = _coerce_column(df[col], pg_type)
            df[col] = coerced
            if failures > 0:
                report["type_coercion_failures"][col] = failures
        except Exception as exc:
            report["type_coercion_failures"][col] = str(exc)

    # ── 3. Duplicate removal ───────────────────────────────────────────────
    before_dedup = len(df)
    df.drop_duplicates(inplace=True)
    report["rows_dropped_duplicates"] = before_dedup - len(df)

    df.reset_index(drop=True, inplace=True)
    report["total_rows_after"] = len(df)

    # ── 4. LLM cleaning suggestions (optional) ────────────────────────────
    if not skip_llm and _COHERE_API_KEY:
        report["llm_suggestions"] = _generate_llm_suggestions(df, column_specs, report)

    return df, report


def _generate_llm_suggestions(
    df: pd.DataFrame,
    column_specs: list[ColumnSpec],
    report: CleaningReport,
) -> list[str]:
    """
    Ask Cohere for data-quality improvement hints based on the cleaning report
    and a statistical summary of the DataFrame.
    """
    null_pct = (df.isna().sum() / len(df) * 100).round(1).to_dict()
    high_null = {k: v for k, v in null_pct.items() if v > 10}

    schema_summary = ", ".join(
        f"{s['name']} ({s['pg_type']})" for s in column_specs
    )

    prompt = f"""A CSV file was uploaded and cleaned. Here is a summary:

Columns: {schema_summary}
Rows after cleaning: {report['total_rows_after']}
Duplicate rows removed: {report['rows_dropped_duplicates']}
Null strings replaced: {report['null_strings_replaced']}
Columns with >10% nulls: {high_null or 'none'}
Type coercion failures: {report['type_coercion_failures'] or 'none'}

Give me exactly 3 short, actionable data quality improvement suggestions for this dataset.
Return only a numbered list — no extra text, no markdown, no explanations."""

    payload = {
        "model": "command-r-08-2024",
        "messages": [
            {
                "role": "system",
                "content": "You are a data quality expert. Give concise, actionable suggestions.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 250,
    }

    try:
        r = requests.post(_COHERE_URL, headers=_COHERE_HEADERS, json=payload, timeout=15)
        if r.status_code >= 400:
            return []
        blocks = r.json().get("message", {}).get("content", [])
        text = next((b.get("text", "") for b in blocks if b.get("type") == "text"), "")
        lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
        # Keep only numbered lines
        suggestions = [ln for ln in lines if ln and ln[0].isdigit()]
        return suggestions[:3]
    except Exception:
        return []
