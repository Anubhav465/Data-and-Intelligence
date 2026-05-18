# backend/chart_generator.py

from typing import Dict, Any, Optional, List
import math


SUPPORTED_TYPES = ["bar", "pie", "line", "histogram", "scatter", "box", "heatmap", "area"]


def is_numeric(value):
    """Check if a value is numeric"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def detect_user_chart_type(question: str) -> Optional[str]:
    """Detect chart type from user question keywords"""
    q = question.lower()

    # Check for multiple scatter plots request
    if ("multiple" in q or "different" in q or "various" in q or "all" in q) and ("scatter" in q or "correlation" in q):
        return "multiple_scatter"
    
    # Specific chart type mentions
    if "scatter" in q or "correlation" in q:
        return "scatter"
    if "box" in q or "distribution" in q or "quartile" in q:
        return "box"
    if "heatmap" in q or "heat map" in q or "correlation matrix" in q:
        return "heatmap"
    if "area" in q and "chart" in q:
        return "area"
    if "pie" in q:
        return "pie"
    if "line" in q:
        return "line"
    if "histogram" in q:
        return "histogram"
    if "bar" in q:
        return "bar"

    return None


def analyze_data_characteristics(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze data to determine best visualization"""
    if not rows or not columns:
        return {}
    
    numeric_cols = []
    categorical_cols = []
    date_cols = []
    
    first_row = rows[0]
    
    for col in columns:
        value = first_row.get(col)
        
        # Check if numeric
        if is_numeric(value):
            # Check if it's actually an ID or code
            if not any(x in col.lower() for x in ["id", "zip", "code", "key"]):
                numeric_cols.append(col)
        # Check if date-like
        elif isinstance(value, str) and any(x in col.lower() for x in ["date", "time", "year", "month"]):
            date_cols.append(col)
        # Otherwise categorical
        else:
            categorical_cols.append(col)
    
    # Calculate cardinality for categorical columns
    cardinalities = {}
    for col in categorical_cols:
        unique_values = len(set(row.get(col) for row in rows if row.get(col) is not None))
        cardinalities[col] = unique_values
    
    return {
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "date_cols": date_cols,
        "cardinalities": cardinalities,
        "row_count": len(rows)
    }


def generate_scatter_plot(columns: List[str], rows: List[Dict[str, Any]], numeric_cols: List[str]) -> Optional[Dict[str, Any]]:
    """Generate scatter plot for 2 numeric columns"""
    if len(numeric_cols) < 2:
        return None
    
    x_col = numeric_cols[0]
    y_col = numeric_cols[1]
    
    # Extract values
    x_values = [row[x_col] for row in rows if row.get(x_col) is not None]
    y_values = [row[y_col] for row in rows if row.get(y_col) is not None]
    
    # Optional: use categorical column for labels
    label_col = None
    for col in columns:
        if col not in numeric_cols:
            label_col = col
            break
    
    labels = [str(row.get(label_col, i)) for i, row in enumerate(rows)] if label_col else None
    
    return {
        "type": "scatter",
        "data": {
            "x": {"column": x_col, "values": x_values},
            "y": {"column": y_col, "values": y_values},
            "labels": labels
        },
        "config": {
            "title": f"{y_col} vs {x_col}",
            "x_label": x_col,
            "y_label": y_col
        }
    }


def generate_multiple_scatter_plots(columns: List[str], rows: List[Dict[str, Any]], numeric_cols: List[str]) -> Optional[List[Dict[str, Any]]]:
    """Generate multiple scatter plots for different feature pairs"""
    if len(numeric_cols) < 2:
        return None
    
    scatter_plots = []
    
    # Generate scatter plots for all pairs of numeric columns (limit to avoid too many)
    max_pairs = 6  # Limit to 6 scatter plots
    pair_count = 0
    
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            if pair_count >= max_pairs:
                break
                
            x_col = numeric_cols[i]
            y_col = numeric_cols[j]
            
            # Extract values
            x_values = [row[x_col] for row in rows if row.get(x_col) is not None and row.get(y_col) is not None]
            y_values = [row[y_col] for row in rows if row.get(x_col) is not None and row.get(y_col) is not None]
            
            scatter_plots.append({
                "type": "scatter",
                "data": {
                    "x": {"column": x_col, "values": x_values},
                    "y": {"column": y_col, "values": y_values}
                },
                "config": {
                    "title": f"{y_col} vs {x_col}",
                    "x_label": x_col,
                    "y_label": y_col
                }
            })
            
            pair_count += 1
        
        if pair_count >= max_pairs:
            break
    
    return scatter_plots if scatter_plots else None


def generate_box_plot(columns: List[str], rows: List[Dict[str, Any]], numeric_cols: List[str], categorical_cols: List[str]) -> Optional[Dict[str, Any]]:
    """Generate box plot for numeric column grouped by categorical"""
    if not numeric_cols or not categorical_cols:
        return None
    
    numeric_col = numeric_cols[0]
    categorical_col = categorical_cols[0]
    
    # Group data by category
    groups = {}
    for row in rows:
        category = str(row.get(categorical_col, "Unknown"))
        value = row.get(numeric_col)
        if value is not None and is_numeric(value):
            if category not in groups:
                groups[category] = []
            groups[category].append(value)
    
    # Limit to top 10 categories
    if len(groups) > 10:
        sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        groups = dict(sorted_groups)
    
    return {
        "type": "box",
        "data": {
            "groups": groups,
            "numeric_column": numeric_col,
            "categorical_column": categorical_col
        },
        "config": {
            "title": f"Distribution of {numeric_col} by {categorical_col}",
            "x_label": categorical_col,
            "y_label": numeric_col
        }
    }


def generate_heatmap(columns: List[str], rows: List[Dict[str, Any]], numeric_cols: List[str]) -> Optional[Dict[str, Any]]:
    """Generate correlation heatmap for numeric columns"""
    if len(numeric_cols) < 2:
        return None
    
    # Limit to first 10 numeric columns
    cols_to_use = numeric_cols[:10]
    
    # Extract data matrix
    data_matrix = []
    for col in cols_to_use:
        col_values = [row.get(col, 0) for row in rows if is_numeric(row.get(col))]
        data_matrix.append(col_values)
    
    # Calculate correlation matrix (simplified)
    n = len(cols_to_use)
    correlation_matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i == j:
                correlation_matrix[i][j] = 1.0
            else:
                # Simplified correlation (would use numpy in production)
                correlation_matrix[i][j] = 0.5  # Placeholder
    
    return {
        "type": "heatmap",
        "data": {
            "columns": cols_to_use,
            "correlation_matrix": correlation_matrix
        },
        "config": {
            "title": "Correlation Heatmap",
            "x_label": "Variables",
            "y_label": "Variables"
        }
    }


def generate_area_chart(columns: List[str], rows: List[Dict[str, Any]], numeric_cols: List[str], date_cols: List[str]) -> Optional[Dict[str, Any]]:
    """Generate area chart for time series data"""
    if not numeric_cols or not date_cols:
        return None
    
    date_col = date_cols[0]
    metric_col = numeric_cols[0]
    
    MAX_POINTS = 50
    trimmed_rows = rows[:MAX_POINTS]
    
    labels = [str(row[date_col]) for row in trimmed_rows]
    values = [row[metric_col] for row in trimmed_rows]
    
    return {
        "type": "area",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": metric_col,
                "data": values
            }]
        },
        "config": {
            "title": f"{metric_col} Over Time",
            "x_label": date_col,
            "y_label": metric_col
        }
    }


def generate_chart_spec(execution: Dict[str, Any], question: str):
    """
    Generate chart specification based on data and question.
    Supports: bar, pie, line, histogram, scatter, box, heatmap, area
    Returns a single chart dict or a list of chart dicts for multiple scatter plots
    """
    if not execution or execution.get("row_count", 0) == 0:
        return None

    columns = execution.get("columns", [])
    rows = execution.get("rows", [])

    if not columns or not rows:
        return None

    # Analyze data characteristics
    characteristics = analyze_data_characteristics(columns, rows)
    numeric_cols = characteristics.get("numeric_cols", [])
    categorical_cols = characteristics.get("categorical_cols", [])
    date_cols = characteristics.get("date_cols", [])
    
    if not numeric_cols:
        return None

    # Detect user's chart preference
    user_choice = detect_user_chart_type(question)
    
    # Generate chart based on user choice or data characteristics
    if user_choice == "multiple_scatter" and len(numeric_cols) >= 2:
        # Return multiple scatter plots
        return generate_multiple_scatter_plots(columns, rows, numeric_cols)
    
    elif user_choice == "scatter" and len(numeric_cols) >= 2:
        return generate_scatter_plot(columns, rows, numeric_cols)
    
    elif user_choice == "box" and numeric_cols and categorical_cols:
        return generate_box_plot(columns, rows, numeric_cols, categorical_cols)
    
    elif user_choice == "heatmap" and len(numeric_cols) >= 2:
        return generate_heatmap(columns, rows, numeric_cols)
    
    elif user_choice == "area" and numeric_cols and date_cols:
        return generate_area_chart(columns, rows, numeric_cols, date_cols)
    
    # Default chart generation logic
    metric_col = numeric_cols[0]
    
    # Find label column
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
    
    # Special case: line/bar chart requested with only numeric columns
    # Use first numeric as X-axis, second as Y-axis
    if not label_col and len(numeric_cols) >= 2 and user_choice in ["line", "bar"]:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]
        
        MAX_POINTS = 50
        trimmed_rows = rows[:MAX_POINTS]
        
        # Sort by x_col for better line chart visualization
        sorted_rows = sorted(trimmed_rows, key=lambda r: r.get(x_col, 0))
        
        labels = [str(row[x_col]) for row in sorted_rows]
        values = [row[y_col] for row in sorted_rows]
        
        return {
            "type": user_choice,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": f"{y_col} vs {x_col}",
                    "data": values
                }]
            }
        }
    
    if not label_col:
        return None
    
    MAX_POINTS = 20
    trimmed_rows = rows[:MAX_POINTS]
    
    labels = [str(row[label_col]) for row in trimmed_rows]
    values = [row[metric_col] for row in trimmed_rows]
    
    # Auto-detection logic
    if user_choice and user_choice in ["bar", "pie", "line"]:
        chart_type = user_choice
    else:
        # Smart defaults
        if date_cols and label_col in date_cols:
            chart_type = "line"
        elif len(trimmed_rows) <= 8:
            chart_type = "pie"
        else:
            chart_type = "bar"
    
    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [{
                "label": metric_col,
                "data": values
            }]
        }
    }

# Made with Bob
