# backend/app/agents/anomaly_agent.py
"""
Anomaly detection agent using Isolation Forest
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any

from app.models.state import AnomalyDetection, AnalyticsState


class AnomalyAgent:
    """
    Agent that detects anomalies in query results using Isolation Forest.
    
    Useful for identifying outliers in sales, delays, or other metrics.
    """
    
    def __init__(self, contamination: float = 0.1):
        """
        Args:
            contamination: Expected proportion of outliers (default 10%)
        """
        self.contamination = contamination
    
    def detect_anomalies(self, state: AnalyticsState) -> AnalyticsState:
        """
        Detect anomalies in numeric columns of query results.
        
        Uses Isolation Forest algorithm for unsupervised anomaly detection.
        """
        rows = state.get("rows", [])
        columns = state.get("columns", [])
        
        if not rows or len(rows) < 10:
            state["anomalies"] = []
            return state
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(rows)
            
            # Select numeric columns only
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_cols:
                state["anomalies"] = []
                return state
            
            # Prepare data for Isolation Forest
            X = df[numeric_cols].fillna(df[numeric_cols].median())
            
            # Train Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            
            predictions = iso_forest.fit_predict(X)
            scores = iso_forest.score_samples(X)
            
            # Find anomalies (predictions == -1)
            anomaly_indices = np.where(predictions == -1)[0].tolist()
            anomaly_scores = scores[anomaly_indices].tolist()
            
            if anomaly_indices:
                # Build description
                description = self._build_anomaly_description(
                    df,
                    anomaly_indices,
                    numeric_cols
                )
                
                state["anomalies"] = [
                    f"Found {len(anomaly_indices)} anomalies in the data",
                    description
                ]
            else:
                state["anomalies"] = []
            
        except Exception as e:
            state["anomalies"] = []
            # Don't fail the entire workflow on anomaly detection errors
            print(f"Anomaly detection error: {str(e)}")
        
        return state
    
    def _build_anomaly_description(
        self,
        df: pd.DataFrame,
        anomaly_indices: List[int],
        numeric_cols: List[str]
    ) -> str:
        """Build human-readable description of anomalies"""
        
        if not anomaly_indices:
            return "No significant anomalies detected"
        
        # Get anomalous rows
        anomalous_rows = df.iloc[anomaly_indices]
        
        # Find which columns have extreme values
        descriptions = []
        
        for col in numeric_cols[:3]:  # Limit to 3 columns
            col_mean = df[col].mean()
            col_std = df[col].std()
            
            anomalous_values = anomalous_rows[col]
            extreme_values = anomalous_values[
                (anomalous_values > col_mean + 2 * col_std) |
                (anomalous_values < col_mean - 2 * col_std)
            ]
            
            if len(extreme_values) > 0:
                descriptions.append(
                    f"{col}: {len(extreme_values)} extreme values detected"
                )
        
        if descriptions:
            return "; ".join(descriptions)
        else:
            return f"{len(anomaly_indices)} rows show unusual patterns"

# Made with Bob
