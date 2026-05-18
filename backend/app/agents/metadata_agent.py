# backend/app/agents/metadata_agent.py
"""
Metadata agent for schema and column information queries.
Handles dataset structure questions without SQL generation.
"""
import pandas as pd
from typing import Dict, Any, List
from app.models.state import AnalyticsState

# Import existing table metadata functions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from table_creator import get_table_metadata
from query_executor import execute_upload_query, execute_query


class MetadataAgent:
    """
    Agent that answers questions about table schema and structure.
    
    Handles queries like:
    - Show me all column names and their data types
    - What is the shape of my dataset? (rows, columns)
    - Are there any missing values in any column?
    - Show me the first 10 rows of data
    - Give me summary statistics for all numeric columns
    """
    
    def answer_metadata_question(self, state: AnalyticsState) -> AnalyticsState:
        """
        Answer metadata questions about table structure.
        Detects the specific type of metadata query and routes accordingly.
        """
        question = state["question"].lower()
        table_names = state.get("table_names", [])
        
        if not table_names:
            state["error"] = "No table specified for metadata query"
            state["summary"] = "Please upload a dataset first to view its metadata."
            return state
        
        table_name = table_names[0]  # Use first table
        
        try:
            # Detect metadata query type
            if any(word in question for word in ["column", "field", "attribute", "data type", "dtype"]):
                return self._get_columns_and_types(state, table_name)
            elif any(word in question for word in ["shape", "dimension", "size", "how many rows", "how many columns"]):
                return self._get_shape(state, table_name)
            elif any(word in question for word in ["missing", "null", "nan", "empty"]):
                return self._get_missing_values(state, table_name)
            elif any(word in question for word in ["first", "preview", "head", "show me", "display"]):
                return self._get_preview(state, table_name, question)
            elif any(word in question for word in ["statistic", "summary", "describe", "mean", "median", "std"]):
                return self._get_statistics(state, table_name)
            else:
                # Default: show comprehensive metadata
                return self._get_comprehensive_metadata(state, table_name)
                
        except Exception as e:
            state["error"] = f"Metadata query failed: {str(e)}"
            state["summary"] = "Error retrieving table metadata."
            return state
    
    def _get_columns_and_types(self, state: AnalyticsState, table_name: str) -> AnalyticsState:
        """Get all column names and their data types"""
        meta = get_table_metadata(table_name)
        
        if not meta:
            state["error"] = f"Table '{table_name}' not found"
            return state
        
        columns = meta["column_specs"]
        
        # Build structured response
        column_info = []
        for col in columns:
            column_info.append({
                "name": col["name"],
                "original_name": col["original_name"],
                "postgres_type": col["pg_type"],
                "pandas_type": col["pandas_type"]
            })
        
        # Build summary
        summary_lines = [
            f"📊 **Column Information for '{table_name}'**\n",
            f"Total Columns: {len(columns)}\n"
        ]
        
        for i, col in enumerate(column_info, 1):
            summary_lines.append(
                f"{i}. **{col['name']}** - Type: {col['postgres_type']} (Pandas: {col['pandas_type']})"
            )
        
        state["data"] = {
            "columns": column_info,
            "column_count": len(columns),
            "table_name": table_name
        }
        state["summary"] = "\n".join(summary_lines)
        state["error"] = None
        
        return state
    
    def _get_shape(self, state: AnalyticsState, table_name: str) -> AnalyticsState:
        """Get dataset shape (rows × columns)"""
        meta = get_table_metadata(table_name)
        
        if not meta:
            state["error"] = f"Table '{table_name}' not found"
            return state
        
        row_count = meta["row_count"]
        column_count = len(meta["column_specs"])
        
        state["data"] = {
            "shape": {
                "rows": row_count,
                "columns": column_count
            },
            "table_name": table_name
        }
        
        state["summary"] = f"📐 **Dataset Shape for '{table_name}'**\n\n" \
                          f"• Rows: {row_count:,}\n" \
                          f"• Columns: {column_count}\n" \
                          f"• Total Cells: {row_count * column_count:,}"
        state["error"] = None
        
        return state
    
    def _get_missing_values(self, state: AnalyticsState, table_name: str) -> AnalyticsState:
        """Check for missing values in each column"""
        meta = get_table_metadata(table_name)
        
        if not meta:
            state["error"] = f"Table '{table_name}' not found"
            return state
        
        columns = meta["column_specs"]
        column_names = [col["name"] for col in columns]
        
        # Query to count NULL values per column
        null_checks = []
        for col_name in column_names:
            null_checks.append(f'SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END) as "{col_name}_nulls"')
        
        sql = f'SELECT {", ".join(null_checks)} FROM uploads."{table_name}"'
        
        result = execute_upload_query(sql, [table_name])
        
        if "error" in result:
            state["error"] = result["error"]
            return state
        
        # Parse results
        null_counts = result["rows"][0] if result["rows"] else {}
        total_rows = meta["row_count"]
        
        missing_info = []
        has_missing = False
        
        for col_name in column_names:
            null_count = null_counts.get(f"{col_name}_nulls", 0)
            if null_count > 0:
                has_missing = True
            percentage = (null_count / total_rows * 100) if total_rows > 0 else 0
            missing_info.append({
                "column": col_name,
                "missing_count": null_count,
                "missing_percentage": round(percentage, 2),
                "has_missing": null_count > 0
            })
        
        # Build summary
        if not has_missing:
            summary = f"✅ **No Missing Values Found**\n\nAll {len(column_names)} columns in '{table_name}' are complete with no NULL values."
        else:
            summary_lines = [f"⚠️ **Missing Values Report for '{table_name}'**\n"]
            columns_with_missing = [info for info in missing_info if info["has_missing"]]
            
            summary_lines.append(f"Columns with missing values: {len(columns_with_missing)} out of {len(column_names)}\n")
            
            for info in columns_with_missing:
                summary_lines.append(
                    f"• **{info['column']}**: {info['missing_count']:,} missing ({info['missing_percentage']:.1f}%)"
                )
            
            summary = "\n".join(summary_lines)
        
        state["data"] = {
            "missing_values": missing_info,
            "has_missing": has_missing,
            "total_rows": total_rows,
            "table_name": table_name
        }
        state["summary"] = summary
        state["error"] = None
        
        return state
    
    def _get_preview(self, state: AnalyticsState, table_name: str, question: str) -> AnalyticsState:
        """Show first N rows of data"""
        # Extract number of rows from question
        import re
        match = re.search(r'(\d+)', question)
        limit = int(match.group(1)) if match else 10
        limit = min(limit, 100)  # Cap at 100 rows
        
        sql = f'SELECT * FROM uploads."{table_name}" LIMIT {limit}'
        result = execute_upload_query(sql, [table_name])
        
        if "error" in result:
            state["error"] = result["error"]
            return state
        
        meta = get_table_metadata(table_name)
        total_rows = meta["row_count"] if meta else 0
        
        state["data"] = result
        state["rows"] = result.get("rows", [])
        state["columns"] = result.get("columns", [])
        state["row_count"] = len(result.get("rows", []))
        
        state["summary"] = f"📋 **Preview of '{table_name}'**\n\n" \
                          f"Showing first {limit} rows out of {total_rows:,} total rows\n" \
                          f"Columns: {len(result.get('columns', []))}"
        state["error"] = None
        
        return state
    
    def _get_statistics(self, state: AnalyticsState, table_name: str) -> AnalyticsState:
        """Get summary statistics for numeric columns"""
        meta = get_table_metadata(table_name)
        
        if not meta:
            state["error"] = f"Table '{table_name}' not found"
            return state
        
        # Identify numeric columns
        numeric_columns = []
        for col in meta["column_specs"]:
            if col["pg_type"] in ["INTEGER", "BIGINT", "NUMERIC", "DOUBLE PRECISION", "REAL"]:
                numeric_columns.append(col["name"])
        
        if not numeric_columns:
            state["summary"] = f"ℹ️ No numeric columns found in '{table_name}' to calculate statistics."
            state["error"] = None
            return state
        
        # Build SQL for statistics
        stat_queries = []
        for col in numeric_columns:
            stat_queries.append(f'''
                '{col}' as column_name,
                COUNT("{col}") as count,
                AVG("{col}")::NUMERIC(10,2) as mean,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "{col}")::NUMERIC(10,2) as median,
                STDDEV("{col}")::NUMERIC(10,2) as std,
                MIN("{col}")::NUMERIC(10,2) as min,
                MAX("{col}")::NUMERIC(10,2) as max
            ''')
        
        sql = f'''
            SELECT * FROM (
                {" UNION ALL ".join(f"SELECT {sq} FROM uploads.\"{table_name}\"" for sq in stat_queries)}
            ) stats
        '''
        
        result = execute_upload_query(sql, [table_name])
        
        if "error" in result:
            state["error"] = result["error"]
            return state
        
        # Build summary
        summary_lines = [f"📊 **Summary Statistics for '{table_name}'**\n"]
        summary_lines.append(f"Numeric columns analyzed: {len(numeric_columns)}\n")
        
        for row in result.get("rows", []):
            summary_lines.append(f"\n**{row['column_name']}**")
            summary_lines.append(f"  • Count: {row['count']:,}")
            summary_lines.append(f"  • Mean: {row['mean']}")
            summary_lines.append(f"  • Median: {row['median']}")
            summary_lines.append(f"  • Std Dev: {row['std']}")
            summary_lines.append(f"  • Min: {row['min']}")
            summary_lines.append(f"  • Max: {row['max']}")
        
        state["data"] = {
            "statistics": result.get("rows", []),
            "numeric_columns": numeric_columns,
            "table_name": table_name
        }
        state["summary"] = "\n".join(summary_lines)
        state["error"] = None
        
        return state
    
    def _get_comprehensive_metadata(self, state: AnalyticsState, table_name: str) -> AnalyticsState:
        """Get comprehensive metadata overview"""
        meta = get_table_metadata(table_name)
        
        if not meta:
            state["error"] = f"Table '{table_name}' not found"
            return state
        
        columns = meta["column_specs"]
        row_count = meta["row_count"]
        
        # Categorize columns by type
        numeric_cols = []
        text_cols = []
        date_cols = []
        
        for col in columns:
            pg_type = col["pg_type"]
            if pg_type in ["INTEGER", "BIGINT", "NUMERIC", "DOUBLE PRECISION", "REAL"]:
                numeric_cols.append(col["name"])
            elif pg_type in ["TEXT", "VARCHAR"]:
                text_cols.append(col["name"])
            elif pg_type in ["TIMESTAMP", "DATE"]:
                date_cols.append(col["name"])
        
        summary_lines = [
            f"📊 **Comprehensive Metadata for '{table_name}'**\n",
            f"**Dataset Shape:**",
            f"  • Rows: {row_count:,}",
            f"  • Columns: {len(columns)}",
            f"  • Total Cells: {row_count * len(columns):,}\n",
            f"**Column Types:**",
            f"  • Numeric: {len(numeric_cols)} columns",
            f"  • Text: {len(text_cols)} columns",
            f"  • Date/Time: {len(date_cols)} columns\n",
            f"**All Columns:**"
        ]
        
        for i, col in enumerate(columns, 1):
            summary_lines.append(f"  {i}. {col['name']} ({col['pg_type']})")
        
        state["data"] = {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [{"name": c["name"], "type": c["pg_type"]} for c in columns],
            "numeric_columns": numeric_cols,
            "text_columns": text_cols,
            "date_columns": date_cols
        }
        state["summary"] = "\n".join(summary_lines)
        state["error"] = None
        
        return state

# Made with Bob
