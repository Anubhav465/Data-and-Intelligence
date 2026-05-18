# backend/app/agents/summary_agent.py
"""
Summary generation agent with structured outputs
"""
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.models.state import SummaryResponse, AnalyticsState

load_dotenv()


class SummaryAgent:
    """
    Agent that generates executive summaries from query results.
    
    Uses structured outputs to ensure exactly 3 bullet points.
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.2):
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.parser = PydanticOutputParser(pydantic_object=SummaryResponse)
    
    def generate_summary(self, state: AnalyticsState) -> AnalyticsState:
        """
        Generate a concise executive summary from query results.
        
        Returns exactly 3 bullet points and a key insight.
        """
        question = state["question"]
        rows = state.get("rows", [])
        
        if not rows:
            state["summary"] = "No data available for this query."
            return state
        
        # Limit to first 15 rows for summary generation
        sample_rows = rows[:15]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert business analyst specializing in data insights.

Your task is to analyze query results and provide actionable insights.

RULES:
1. Generate exactly 3 concise bullet points
2. Each bullet must be one short sentence (max 20 words)
3. Use real numbers and exact insights from the data
4. Focus on the most important findings
5. Be specific and actionable
6. Identify the single most important insight

Your response must be valid JSON matching the SummaryResponse schema."""),
            ("human", """Question: {question}

Data sample (first 15 rows):
{data_sample}

Analyze this data and provide insights.

{format_instructions}""")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "question": question,
                "data_sample": str(sample_rows),
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Format bullet points
            formatted_bullets = "\n".join(
                f"• {bullet}" for bullet in result.bullet_points
            )
            
            state["summary"] = formatted_bullets
            state["error"] = None
            
        except Exception as e:
            state["summary"] = "Summary generation failed."
            state["error"] = f"Summary error: {str(e)}"
        
        return state

# Made with Bob
