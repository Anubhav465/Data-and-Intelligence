# backend/chart_generator.py

from typing import Dict, Any, Optional
import math


SUPPORTED_TYPES = ["bar", "pie", "line", "histogram"]


def is_numeric(value):
    return isinstance(value, (int, float))


def detect_user_chart_type(question: str) -> Optional[str]:
    q = question.lower()

    if "pie" in q:
        return "pie"
    if "line" in q:
        return "line"
    if "histogram" in q:
        return "histogram"
    if "bar" in q:
        return "bar"

    return None


def generate_chart_spec(execution: Dict[str, Any], question: str):

    if not execution or execution.get("row_count", 0) == 0:
        return None

    columns = execution.get("columns", [])
    rows = execution.get("rows", [])

    if not columns or not rows:
        return None

    # Detect numeric columns
    numeric_cols = []
    for col in columns:
        if is_numeric(rows[0].get(col)):
            if not any(x in col.lower() for x in ["id", "zip", "code"]):
                numeric_cols.append(col)

    if not numeric_cols:
        return None

    metric_col = numeric_cols[0]

    # Detect label column
    label_col = None
    for col in columns:
        if col != metric_col and col not in numeric_cols:
            label_col = col
            break

    # Histogram case (single numeric column only)
    if len(columns) == 1 and metric_col:
        values = [row[metric_col] for row in rows]
        return {
            "type": "histogram",
            "data": {
                "values": values,
                "label": metric_col
            }
        }

    if not label_col:
        return None

    MAX_POINTS = 20
    trimmed_rows = rows[:MAX_POINTS]

    labels = [str(row[label_col]) for row in trimmed_rows]
    values = [row[metric_col] for row in trimmed_rows]

    # Detect chart preference
    user_choice = detect_user_chart_type(question)

    if user_choice in SUPPORTED_TYPES:
        chart_type = user_choice
    else:
        # Auto-detection logic
        if "date" in label_col.lower():
            chart_type = "line"
        elif len(trimmed_rows) <= 8:
            chart_type = "pie"
        else:
            chart_type = "bar"

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": metric_col,
                    "data": values
                }
            ]
        }
    }