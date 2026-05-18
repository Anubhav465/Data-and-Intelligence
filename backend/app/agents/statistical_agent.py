# backend/app/agents/statistical_agent.py
"""
Statistical analysis agent for correlation and feature importance.
"""
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import create_engine
from dotenv import load_dotenv

from app.models.state import AnalyticsState

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


class StatisticalAgent:
    """
    Agent that performs statistical analysis on data.
    
    Handles queries like:
    - Which features are most important?
    - What correlates with X?
    - Feature importance analysis
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
    
    def analyze_feature_importance(self, state: AnalyticsState) -> AnalyticsState:
        """
        Perform feature importance analysis using Random Forest.
        
        Automatically detects target variable and performs analysis.
        """
        table_names = state.get("table_names", [])
        question = state["question"]
        
        if not table_names:
            state["error"] = "No table specified for statistical analysis"
            return state
        
        table_name = table_names[0]
        
        try:
            # Load data
            query = f'SELECT * FROM uploads."{table_name}" LIMIT 5000'
            df = pd.read_sql(query, self.engine)
            
            if len(df) < 10:
                state["error"] = "Not enough data for statistical analysis"
                state["summary"] = "Need at least 10 rows for analysis."
                return state
            
            # Detect target variable from question
            target_col = self._detect_target_variable(question, df.columns)
            
            if not target_col:
                # Try to find a column named 'outcome', 'target', 'label', etc.
                for col in df.columns:
                    if col.lower() in ['outcome', 'target', 'label', 'class', 'result']:
                        target_col = col
                        break
            
            if not target_col:
                state["error"] = "Could not identify target variable"
                state["summary"] = "Please specify which column to predict (e.g., 'predict diabetes')."
                return state
            
            # Prepare features and target
            X = df.drop(columns=[target_col])
            y = df[target_col]
            
            # Handle non-numeric columns
            X_numeric = X.select_dtypes(include=[np.number])
            
            if len(X_numeric.columns) == 0:
                state["error"] = "No numeric features found"
                state["summary"] = "Need numeric columns for feature importance analysis."
                return state
            
            # Fill missing values
            X_numeric = X_numeric.fillna(X_numeric.median())
            
            # Determine if classification or regression
            is_classification = len(y.unique()) < 20 and y.dtype in ['object', 'int64', 'bool']
            
            if is_classification:
                # Encode target if needed
                if y.dtype == 'object':
                    le = LabelEncoder()
                    y = le.fit_transform(y)
                
                model = RandomForestClassifier(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
            
            # Train model
            model.fit(X_numeric, y)
            
            # Get feature importances
            importances = sorted(
                zip(X_numeric.columns, model.feature_importances_),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Build response
            feature_importance_data = [
                {
                    "feature": col,
                    "importance": float(score),
                    "percentage": float(score * 100)
                }
                for col, score in importances
            ]
            
            # Build summary
            top_features = importances[:5]
            summary_parts = [
                f"• Top predictor of {target_col}: {top_features[0][0]} ({top_features[0][1]*100:.1f}%)",
                f"• Second most important: {top_features[1][0]} ({top_features[1][1]*100:.1f}%)",
                f"• Third: {top_features[2][0]} ({top_features[2][1]*100:.1f}%)"
            ]
            
            state["data"] = {
                "feature_importance": feature_importance_data,
                "target_variable": target_col,
                "model_type": "classification" if is_classification else "regression",
                "num_features": len(X_numeric.columns)
            }
            state["summary"] = "\n".join(summary_parts)
            state["error"] = None
            
        except Exception as e:
            state["error"] = f"Statistical analysis failed: {str(e)}"
            state["summary"] = "Error performing feature importance analysis."
        
        return state
    
    def _detect_target_variable(self, question: str, columns: list) -> str:
        """
        Detect target variable from question.
        
        Examples:
        - "predict diabetes" → "diabetes"
        - "associated with outcome" → "outcome"
        - "features for churn" → "churn"
        """
        question_lower = question.lower()
        
        # Keywords that indicate target variable
        keywords = ['predict', 'associated with', 'correlate with', 'for', 'of']
        
        for col in columns:
            col_lower = col.lower()
            # Check if column name appears after keywords
            for keyword in keywords:
                if keyword in question_lower and col_lower in question_lower:
                    # Check if column appears after keyword
                    keyword_pos = question_lower.find(keyword)
                    col_pos = question_lower.find(col_lower)
                    if col_pos > keyword_pos:
                        return col
        
        return None

# Made with Bob
