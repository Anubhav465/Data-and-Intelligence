# backend/app/agents/metadata_agent.py
"""
Metadata agent for schema and column information queries.
"""
from app.models.state import AnalyticsState

# Import existing table metadata functions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from table_creator import get_table_metadata


class MetadataAgent:
    """
    Agent that answers questions about table schema and structure.
    
    Handles queries like:
    - How many columns are there?
    - What are the column names?
    - What data types are used?
    - Show me the schema
    """
    
    def answer_metadata_question(self, state: AnalyticsState) -> AnalyticsState:
        """
        Answer metadata questions about table structure.
        """
        table_names = state.get("table_names", [])
        
        if not table_names:
            state["error"] = "No table specified for metadata query"
            state["summary"] = "Please specify which table you want to know about."
            return state
        
        table_name = table_names[0]  # Use first table
        
        try:
            meta = get_table_metadata(table_name)
            
            if not meta:
                state["error"] = f"Table '{table_name}' not found"
                state["summary"] = f"Table '{table_name}' does not exist."
                return state
            
            columns = meta["column_specs"]
            
            # Build response data
            response_data = {
                "table_name": table_name,
                "column_count": len(columns),
                "row_count": meta["row_count"],
                "columns": [
                    {
                        "name": col["name"],
                        "original_name": col["original_name"],
                        "type": col["pg_type"],
                        "pandas_type": col["pandas_type"]
                    }
                    for col in columns
                ],
                "created_at": meta.get("created_at")
            }
            
            # Build summary
            column_names = [col["name"] for col in columns]
            summary_parts = [
                f"• Table '{table_name}' has {len(columns)} columns and {meta['row_count']} rows",
                f"• Columns: {', '.join(column_names[:10])}{'...' if len(column_names) > 10 else ''}",
                f"• Data types: {', '.join(set(col['pg_type'] for col in columns))}"
            ]
            
            state["data"] = {"metadata": response_data}
            state["summary"] = "\n".join(summary_parts)
            state["error"] = None
            
        except Exception as e:
            state["error"] = f"Metadata query failed: {str(e)}"
            state["summary"] = "Error retrieving table metadata."
        
        return state

# Made with Bob
