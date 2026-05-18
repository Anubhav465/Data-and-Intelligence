# backend/app/agents/forecast_agent.py
"""
Forecasting agent using Prophet
"""
import pandas as pd
from prophet import Prophet
from typing import Optional
from datetime import datetime, timedelta

from app.models.state import ForecastResult, AnalyticsState


class ForecastAgent:
    """
    Agent that generates time-series forecasts using Facebook Prophet.
    
    Useful for predicting future sales, orders, or trends.
    """
    
    def __init__(self, periods: int = 30):
        """
        Args:
            periods: Number of future periods to forecast (default 30 days)
        """
        self.periods = periods
    
    def generate_forecast(self, state: AnalyticsState) -> AnalyticsState:
        """
        Generate time-series forecast if data contains date column.
        
        Requires:
        - A date/timestamp column
        - A numeric column to forecast
        - At least 10 historical data points
        """
        rows = state.get("rows", [])
        columns = state.get("columns", [])
        
        if not rows or len(rows) < 10:
            state["forecast"] = None
            return state
        
        try:
            df = pd.DataFrame(rows)
            
            # Find date column
            date_col = self._find_date_column(df)
            if not date_col:
                state["forecast"] = None
                return state
            
            # Find numeric column to forecast
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if not numeric_cols:
                state["forecast"] = None
                return state
            
            # Use first numeric column as target
            target_col = numeric_cols[0]
            
            # Prepare data for Prophet
            prophet_df = pd.DataFrame({
                'ds': pd.to_datetime(df[date_col]),
                'y': df[target_col]
            })
            
            # Remove duplicates and sort
            prophet_df = prophet_df.drop_duplicates(subset=['ds']).sort_values('ds')
            
            # Train Prophet model
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=True,
                interval_width=0.95
            )
            model.fit(prophet_df)
            
            # Make future dataframe
            future = model.make_future_dataframe(periods=self.periods)
            forecast = model.predict(future)
            
            # Extract forecast for future periods only
            future_forecast = forecast.tail(self.periods)
            
            # Determine trend
            trend = self._determine_trend(future_forecast['yhat'].tolist())
            
            # Build forecast result
            forecast_data = {
                "forecast_values": future_forecast['yhat'].tolist(),
                "forecast_dates": future_forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                "confidence_intervals": [
                    {
                        "lower": float(row['yhat_lower']),
                        "upper": float(row['yhat_upper'])
                    }
                    for _, row in future_forecast.iterrows()
                ],
                "trend": trend
            }
            
            state["forecast"] = forecast_data
            
        except Exception as e:
            state["forecast"] = None
            # Don't fail the entire workflow on forecast errors
            print(f"Forecast error: {str(e)}")
        
        return state
    
    def _find_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the first date/timestamp column in the dataframe"""
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
            
            # Try to parse as datetime
            try:
                pd.to_datetime(df[col])
                return col
            except:
                continue
        
        return None
    
    def _determine_trend(self, values: list) -> str:
        """Determine if trend is increasing, decreasing, or stable"""
        if len(values) < 2:
            return "stable"
        
        first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
        second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"

# Made with Bob
