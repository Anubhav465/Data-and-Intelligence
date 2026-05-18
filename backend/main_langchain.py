# backend/main_langchain.py
"""
Neural Analytics 3.0 - Main entry point with LangChain/LangGraph

This is the new main file that uses the LangChain-powered workflow.
To use this instead of the old main.py, update your startup command to:
    uvicorn main_langchain:app --reload
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LangSmith tracing (optional but highly recommended)
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "neural-analytics-3.0")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")

# Import the FastAPI app
from app.api.routes import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_langchain:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

# Made with Bob
