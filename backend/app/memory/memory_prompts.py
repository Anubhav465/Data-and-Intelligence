# backend/app/memory/memory_prompts.py
"""
System prompts for memory-aware conversation handling
"""

GREETING_PROMPT = """You are Neural Analytics 2.0, a friendly and helpful AI analytics assistant.

{user_context}

User said: {message}

Respond warmly and naturally. {name_instruction}
Offer to help with data analysis, visualizations, anomaly detection, forecasting, or knowledge graphs.
Keep your response concise (2-3 sentences).
"""

NAME_INTRODUCTION_PROMPT = """You are Neural Analytics 2.0, a friendly AI analytics assistant.

The user just introduced themselves: {message}

Respond warmly, acknowledge their name, and briefly introduce yourself.
Mention that you can help with data analysis, visualizations, and insights.
Keep it friendly and concise (2-3 sentences).
"""

CASUAL_CHAT_PROMPT = """You are Neural Analytics 2.0, a helpful AI analytics assistant.

{user_context}

User asked: {message}

Respond helpfully and professionally. {name_instruction}
If they're asking about your capabilities, mention:
- SQL query generation and data analysis
- Chart and visualization creation
- Anomaly detection
- Time-series forecasting
- Knowledge graph generation
- Natural language data exploration

Keep your response concise and friendly.
"""

OUT_OF_SCOPE_PROMPT = """You are Neural Analytics 2.0, an AI analytics assistant.

{user_context}

User asked: {message}

This question is outside your domain. You specialize in:
- Data analysis and SQL queries
- Chart and visualization creation
- Anomaly detection in datasets
- Time-series forecasting
- Knowledge graph generation
- Statistical analysis

Politely explain that you cannot answer questions about {topic} because you focus on data analytics.
{name_instruction}
Offer to help with their uploaded data instead.
Keep your response friendly and concise (2-3 sentences).
"""

SQL_WITH_MEMORY_PROMPT = """You are a senior PostgreSQL analyst{user_name_context}.

{memory_context}

Current Question: {question}

{schema_context}

Generate SQL that addresses the current question.
{reference_instruction}

Return ONLY the SQL query, no explanations or markdown.
"""


def format_user_context(user_profile: dict, conversation_history: list) -> str:
    """Format user context for prompts"""
    parts = []
    
    if user_profile and user_profile.get("name"):
        parts.append(f"User's name: {user_profile['name']}")
    
    if conversation_history:
        recent = conversation_history[-3:]
        if len(recent) > 0:
            parts.append("\nRecent conversation:")
            for turn in recent:
                parts.append(f"  User: {turn.get('user_message', '')[:100]}")
                parts.append(f"  You: {turn.get('assistant_response', '')[:100]}")
    
    return "\n".join(parts) if parts else "This is a new conversation."


def format_name_instruction(user_name: str = None) -> str:
    """Format name usage instruction"""
    if user_name:
        return f"Use their name ({user_name}) in your response to make it personal."
    return "Be friendly and welcoming."


def format_memory_context(key_findings: list, recent_questions: list) -> str:
    """Format memory context for SQL generation"""
    parts = []
    
    if key_findings:
        parts.append("Previous Findings:")
        for i, finding in enumerate(key_findings[-3:], 1):
            parts.append(f"  {i}. {finding}")
    
    if recent_questions:
        parts.append("\nRecent Questions:")
        for i, q in enumerate(recent_questions[-3:], 1):
            parts.append(f"  {i}. {q}")
    
    return "\n".join(parts) if parts else ""


def format_reference_instruction(has_previous_findings: bool) -> str:
    """Format instruction about referencing previous findings"""
    if has_previous_findings:
        return "If relevant, build upon the previous findings mentioned above."
    return ""


def get_greeting_prompt(message: str, user_profile: dict = None, conversation_history: list = None) -> str:
    """Get formatted greeting prompt"""
    user_context = format_user_context(user_profile or {}, conversation_history or [])
    user_name = user_profile.get("name") if user_profile else None
    name_instruction = format_name_instruction(user_name)
    
    return GREETING_PROMPT.format(
        user_context=user_context,
        message=message,
        name_instruction=name_instruction
    )


def get_name_introduction_prompt(message: str) -> str:
    """Get formatted name introduction prompt"""
    return NAME_INTRODUCTION_PROMPT.format(message=message)


def get_casual_chat_prompt(message: str, user_profile: dict = None, conversation_history: list = None) -> str:
    """Get formatted casual chat prompt"""
    user_context = format_user_context(user_profile or {}, conversation_history or [])
    user_name = user_profile.get("name") if user_profile else None
    name_instruction = format_name_instruction(user_name)
    
    return CASUAL_CHAT_PROMPT.format(
        user_context=user_context,
        message=message,
        name_instruction=name_instruction
    )


def get_out_of_scope_prompt(message: str, topic: str, user_profile: dict = None, conversation_history: list = None) -> str:
    """Get formatted out-of-scope rejection prompt"""
    user_context = format_user_context(user_profile or {}, conversation_history or [])
    user_name = user_profile.get("name") if user_profile else None
    name_instruction = format_name_instruction(user_name)
    
    return OUT_OF_SCOPE_PROMPT.format(
        user_context=user_context,
        message=message,
        topic=topic,
        name_instruction=name_instruction
    )


def get_sql_with_memory_prompt(
    question: str,
    schema_context: str,
    user_name: str = None,
    key_findings: list = None,
    recent_questions: list = None
) -> str:
    """Get formatted SQL generation prompt with memory context"""
    user_name_context = f" for {user_name}" if user_name else ""
    memory_context = format_memory_context(key_findings or [], recent_questions or [])
    reference_instruction = format_reference_instruction(bool(key_findings))
    
    return SQL_WITH_MEMORY_PROMPT.format(
        user_name_context=user_name_context,
        memory_context=memory_context,
        question=question,
        schema_context=schema_context,
        reference_instruction=reference_instruction
    )

# Made with Bob
