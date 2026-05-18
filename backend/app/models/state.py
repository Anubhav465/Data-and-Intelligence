# backend/app/models/state.py
"""
State models for LangGraph workflow
"""
from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalyticsState(TypedDict):
    """
    State object passed through the LangGraph workflow.
    
    This maintains all context as the question flows through different nodes.
    """
    # Input
    question: str
    table_names: Optional[List[str]]
    document_ids: Optional[List[str]]  # For document RAG queries
    
    # Schema context
    schema_context: Optional[str]
    relevant_tables: Optional[List[str]]
    
    # SQL generation
    sql: Optional[str]
    sql_explanation: Optional[str]
    
    # Execution
    data: Optional[Dict[str, Any]]
    columns: Optional[List[str]]
    rows: Optional[List[Dict[str, Any]]]
    row_count: Optional[int]
    
    # Error handling
    error: Optional[str]
    retry_count: int
    
    # Analysis
    chart_spec: Optional[Dict[str, Any]]
    summary: Optional[str]
    anomalies: Optional[List[str]]
    forecast: Optional[Dict[str, Any]]
    knowledge_graph: Optional[Dict[str, Any]]  # Knowledge graph data
    sources: Optional[List[Dict[str, Any]]]  # Document sources for RAG
    
    # Metadata
    execution_time_ms: Optional[float]
    source: Optional[str]
    intent: Optional[str]


class SQLResponse(BaseModel):
    """Structured output for SQL generation"""
    sql: str = Field(description="The generated PostgreSQL query")
    explanation: str = Field(description="Brief explanation of what the query does")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)


class SummaryResponse(BaseModel):
    """Structured output for summary generation"""
    bullet_points: List[str] = Field(description="Exactly 3 concise bullet points")
    key_insight: str = Field(description="Single most important finding")


class ChartRecommendation(BaseModel):
    """Structured output for chart type recommendation"""
    chart_type: str = Field(description="Recommended chart type: bar, pie, line, or histogram")
    reasoning: str = Field(description="Why this chart type is appropriate")
    x_axis: Optional[str] = Field(description="Column for x-axis")
    y_axis: Optional[str] = Field(description="Column for y-axis")


class AnomalyDetection(BaseModel):
    """Structured output for anomaly detection"""
    anomalies_found: bool = Field(description="Whether anomalies were detected")
    anomaly_indices: List[int] = Field(description="Row indices of anomalies")
    anomaly_scores: List[float] = Field(description="Anomaly scores")
    description: str = Field(description="Human-readable description of anomalies")


class ForecastResult(BaseModel):
    """Structured output for forecasting"""
    forecast_values: List[float] = Field(description="Predicted future values")
    forecast_dates: List[str] = Field(description="Dates for predictions")
    confidence_intervals: List[Dict[str, float]] = Field(description="Upper and lower bounds")
    trend: str = Field(description="Overall trend: increasing, decreasing, or stable")


class IntentClassification(BaseModel):
    """Structured output for intent detection"""
    intent: str = Field(description="Primary intent: sql_query, forecast, anomaly, or summary")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
    requires_sql: bool = Field(description="Whether SQL execution is needed")
    requires_forecast: bool = Field(description="Whether forecasting is needed")
    requires_anomaly_detection: bool = Field(description="Whether anomaly detection is needed")

# Made with Bob
