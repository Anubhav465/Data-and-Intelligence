# backend/app/memory/__init__.py
"""
Conversation memory module for Neural Analytics 3.0

Provides session management, conversation history tracking,
and smart summarization for context-aware responses.
"""

from .conversation_memory import ConversationMemory, get_memory_manager
from .memory_prompts import (
    GREETING_PROMPT,
    NAME_INTRODUCTION_PROMPT,
    CASUAL_CHAT_PROMPT,
    OUT_OF_SCOPE_PROMPT,
    SQL_WITH_MEMORY_PROMPT,
    get_greeting_prompt,
    get_name_introduction_prompt,
    get_casual_chat_prompt,
    get_out_of_scope_prompt,
    get_sql_with_memory_prompt,
)
from .memory_summarizer import MemorySummarizer, get_summarizer

__all__ = [
    "ConversationMemory",
    "get_memory_manager",
    "MemorySummarizer",
    "get_summarizer",
    "GREETING_PROMPT",
    "NAME_INTRODUCTION_PROMPT",
    "CASUAL_CHAT_PROMPT",
    "OUT_OF_SCOPE_PROMPT",
    "SQL_WITH_MEMORY_PROMPT",
    "get_greeting_prompt",
    "get_name_introduction_prompt",
    "get_casual_chat_prompt",
    "get_out_of_scope_prompt",
    "get_sql_with_memory_prompt",
]

# Made with Bob
