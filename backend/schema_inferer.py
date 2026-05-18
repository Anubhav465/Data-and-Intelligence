# backend/schema_inferer.py
"""
CSV schema inference: column-name normalisation and pandas→PostgreSQL type mapping.
"""
from __future__ import annotations

import re
from typing import TypedDict

import pandas as pd


# ── Type mapping ───────────────────────────────────────────────────────────
_PANDAS_TO_PG: dict[str, str] = {
    "int8":            "SMALLINT",
    "int16":           "SMALLINT",
    "int32":           "INTEGER",
    "int64":           "BIGINT",
    "Int8":            "SMALLINT",    # nullable integers (pandas 1.0+)
    "Int16":           "SMALLINT",
    "Int32":           "INTEGER",
    "Int64":           "BIGINT",
    "float32":         "REAL",
    "float64":         "DOUBLE PRECISION",
    "bool":            "BOOLEAN",
    "datetime64[ns]":  "TIMESTAMP",
    "object":          "TEXT",
}


class ColumnSpec(TypedDict):
    name: str            # normalised, PG-safe identifier
    original_name: str   # raw CSV header
    pandas_type: str     # pandas dtype string
    pg_type: str         # PostgreSQL data type


# ── Helpers ────────────────────────────────────────────────────────────────

def normalize_column_name(name: str) -> str:
    """
    Produce a lowercase, snake_case PostgreSQL identifier.

    Examples
    --------
    "Order ID"  → "order_id"
    "Price ($)" → "price"
    "2023 Rev"  → "col_2023_rev"
    """
    cleaned = name.strip().lower()
    cleaned = re.sub(r"[^\w]+", "_", cleaned)   # non-word chars → underscore
    cleaned = re.sub(r"_+", "_", cleaned)        # collapse consecutive underscores
    cleaned = cleaned.strip("_")
    if cleaned and cleaned[0].isdigit():
        cleaned = "col_" + cleaned
    return cleaned or "column"


def _try_parse_datetime(series: pd.Series) -> pd.Series | None:
    """
    Return a datetime-parsed copy of *series* only when ≥ 80 % of
    non-null values parse successfully; otherwise return None.
    """
    non_null = series.dropna()
    if len(non_null) < 5:
        return None
    try:
        parsed = pd.to_datetime(non_null, infer_datetime_format=True, errors="coerce")
        ratio = parsed.notna().sum() / len(non_null)
        if ratio >= 0.80:
            return pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
    except Exception:
        pass
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def infer_schema(file_path: str) -> tuple[pd.DataFrame, list[ColumnSpec]]:
    """
    Read *file_path* (CSV), normalise column names, infer PostgreSQL types.

    Returns
    -------
    df           : DataFrame with normalised column names
    column_specs : ordered list of ColumnSpec dicts
    """
    df = pd.read_csv(file_path, low_memory=False)

    # ── Rename columns to safe identifiers ────────────────────────────────
    original: dict[str, str] = {}     # normalised_name → original_header
    seen: dict[str, int] = {}
    rename: dict[str, str] = {}

    for col in df.columns:
        norm = normalize_column_name(str(col))
        if norm in seen:
            seen[norm] += 1
            norm = f"{norm}_{seen[norm]}"
        else:
            seen[norm] = 0
        rename[col] = norm
        original[norm] = str(col)

    df.rename(columns=rename, inplace=True)

    # ── Attempt datetime upgrade for object columns ────────────────────────
    for col in list(df.select_dtypes(include="object").columns):
        upgraded = _try_parse_datetime(df[col])
        if upgraded is not None:
            df[col] = upgraded

    # ── Build column specs ─────────────────────────────────────────────────
    specs: list[ColumnSpec] = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        pg_type = _PANDAS_TO_PG.get(dtype_str, "TEXT")
        specs.append(
            ColumnSpec(
                name=col,
                original_name=original.get(col, col),
                pandas_type=dtype_str,
                pg_type=pg_type,
            )
        )

    return df, specs
