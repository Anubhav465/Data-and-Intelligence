# backend/app/memory/memory_summarizer.py
"""
Smart conversation summarization for memory management

Keeps recent conversations in full detail while summarizing older ones
to control token usage and maintain context.
"""

import os
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()


class MemorySummarizer:
    """
    Manages conversation summarization to keep memory bounded.
    
    Strategy:
    - Keep last 5 turns in full detail
    - Summarize older conversations (>5 turns)
    - Extract key facts: names, preferences, findings
    - Use LLM to create concise summaries
    """
    
    def __init__(self, summarize_after_turns: int = 5):
        """
        Initialize memory summarizer.
        
        Args:
            summarize_after_turns: Number of turns before triggering summarization
        """
        self.summarize_after_turns = summarize_after_turns
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
    
    def should_summarize(self, conversation_history: List[Dict[str, Any]]) -> bool:
        """Check if conversation should be summarized"""
        return len(conversation_history) > self.summarize_after_turns
    
    def summarize_conversation(
        self,
        conversation_history: List[Dict[str, Any]],
        existing_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize conversation history.
        
        Returns:
            {
                "summary": "Concise summary of older conversations",
                "key_facts": ["fact1", "fact2", ...],
                "recent_history": [last 5 turns in full detail]
            }
        """
        if len(conversation_history) <= self.summarize_after_turns:
            return {
                "summary": existing_summary,
                "key_facts": self._extract_key_facts(conversation_history),
                "recent_history": conversation_history
            }
        
        # Split into older and recent
        older_turns = conversation_history[:-self.summarize_after_turns]
        recent_turns = conversation_history[-self.summarize_after_turns:]
        
        # Generate summary of older conversations
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a conversation summarizer. Create a concise summary of the conversation history.

Focus on:
- User's name and preferences
- Key questions asked
- Important findings and insights
- Active datasets/tables

Keep the summary under 200 words."""),
            ("human", """Previous summary (if any):
{existing_summary}

Conversation to summarize:
{conversation}

Create a concise summary that captures the essential information.""")
        ])
        
        # Format older conversation
        conversation_text = self._format_conversation(older_turns)
        
        try:
            chain = summary_prompt | self.llm
            result = chain.invoke({
                "existing_summary": existing_summary or "None",
                "conversation": conversation_text
            })
            
            new_summary = result.content.strip()
        except Exception as e:
            print(f"[Summarizer] Error: {e}")
            new_summary = existing_summary or "Conversation history available."
        
        # Extract key facts from all history
        key_facts = self._extract_key_facts(conversation_history)
        
        return {
            "summary": new_summary,
            "key_facts": key_facts,
            "recent_history": recent_turns
        }
    
    def _format_conversation(self, turns: List[Dict[str, Any]]) -> str:
        """Format conversation turns for summarization"""
        lines = []
        for turn in turns:
            lines.append(f"User: {turn.get('user_message', '')}")
            lines.append(f"Assistant: {turn.get('assistant_response', '')[:200]}...")
            if turn.get('intent'):
                lines.append(f"[Intent: {turn['intent']}]")
            lines.append("")
        return "\n".join(lines)
    
    def _extract_key_facts(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """Extract key facts from conversation history"""
        facts = []
        
        for turn in conversation_history:
            extracted = turn.get("extracted_facts", {})
            
            # User name
            if "user_name" in extracted:
                fact = f"User's name: {extracted['user_name']}"
                if fact not in facts:
                    facts.append(fact)
            
            # Preferences
            if "preferences" in extracted:
                for key, value in extracted["preferences"].items():
                    fact = f"Preference - {key}: {value}"
                    if fact not in facts:
                        facts.append(fact)
            
            # Key findings (from assistant responses mentioning numbers/insights)
            response = turn.get("assistant_response", "")
            if any(keyword in response.lower() for keyword in ["found", "cases", "total", "average", "mean"]):
                # Extract first sentence as potential finding
                sentences = response.split(".")
                if sentences:
                    finding = sentences[0].strip()
                    if len(finding) < 150 and finding not in facts:
                        facts.append(finding)
        
        # Keep only last 10 facts
        return facts[-10:]
    
    def extract_name_from_message(self, message: str) -> Optional[str]:
        """
        Extract user name from introduction message.
        
        Patterns:
        - "My name is X"
        - "I'm X"
        - "I am X"
        - "Call me X"
        """
        message_lower = message.lower()
        
        patterns = [
            "my name is ",
            "i'm ",
            "i am ",
            "call me ",
            "this is "
        ]
        
        for pattern in patterns:
            if pattern in message_lower:
                # Extract name after pattern
                start_idx = message_lower.index(pattern) + len(pattern)
                remaining = message[start_idx:].strip()
                
                # Get first word as name (handle "My name is John Smith" → "John")
                name_parts = remaining.split()
                if name_parts:
                    name = name_parts[0].strip(".,!?")
                    # Capitalize first letter
                    if name and name[0].islower():
                        name = name.capitalize()
                    return name
        
        return None


# Singleton instance
_summarizer: Optional[MemorySummarizer] = None


def get_summarizer() -> MemorySummarizer:
    """Get or create the global summarizer instance"""
    global _summarizer
    
    if _summarizer is None:
        summarize_after = int(os.getenv("SUMMARIZE_AFTER_TURNS", "5"))
        _summarizer = MemorySummarizer(summarize_after_turns=summarize_after)
    
    return _summarizer

# Made with Bob
