# Conversation Memory Implementation Plan

## Overview
Add conversational memory capabilities to Neural Analytics 3.0 so the assistant can:
- Respond naturally to greetings ("Hi" → "Hi! How can I help you today?")
- Remember user names and preferences ("My name is Anubhav" → use name in future responses)
- Maintain conversation history across queries
- Reference previous findings in new answers
- Provide context-aware responses

## Architecture

### 1. Memory Storage Layer
**Location**: `backend/app/memory/`

#### Components:
- **conversation_memory.py**: Hybrid in-memory/Redis session manager
  - In-memory dict for fast access (default)
  - Optional Redis fallback for persistence
  - Session TTL: 24 hours
  - Auto-cleanup of expired sessions

- **memory_summarizer.py**: Smart conversation summarization
  - Keep last 5 full turns in memory
  - Summarize older conversations (>5 turns)
  - Extract key facts: user name, preferences, important findings
  - Use LLM to create concise summaries

- **memory_prompts.py**: System prompts for memory-aware responses
  - Greeting responses
  - Context-aware query handling
  - Cross-referencing previous findings

### 2. Session Management

#### Session Flow:
```
1. User sends first message (no session_id)
   ↓
2. Backend generates UUID session_id
   ↓
3. Backend returns session_id in response
   ↓
4. Frontend stores session_id (localStorage/state)
   ↓
5. Frontend includes session_id in all subsequent requests
   ↓
6. Backend retrieves conversation history for session_id
   ↓
7. Backend updates history after each interaction
```

#### Session Data Structure:
```python
{
    "session_id": "uuid-string",
    "created_at": "2026-05-18T15:30:00Z",
    "last_active": "2026-05-18T15:45:00Z",
    "user_profile": {
        "name": "Anubhav",
        "preferences": {
            "chart_type": "bar",
            "aggregation_style": "percentage"
        }
    },
    "conversation_history": [
        {
            "turn": 1,
            "timestamp": "2026-05-18T15:30:00Z",
            "user_message": "Hi",
            "assistant_response": "Hi! How can I help you today?",
            "intent": "greeting"
        },
        {
            "turn": 2,
            "timestamp": "2026-05-18T15:31:00Z",
            "user_message": "My name is Anubhav",
            "assistant_response": "Nice to meet you, Anubhav! I'm Neural Analytics...",
            "intent": "name_introduction",
            "extracted_facts": {"user_name": "Anubhav"}
        }
    ],
    "key_findings": [
        "357 benign cases, 212 malignant cases",
        "Total 569 cases analyzed"
    ],
    "active_tables": ["user_table_0ddf41f7301f"],
    "conversation_summary": "User introduced themselves as Anubhav..."
}
```

### 3. Workflow Integration

#### Updated Intent Classification:
```python
Intents:
- greeting: "hi", "hello", "hey"
- name_introduction: "my name is X", "I'm X", "call me X"
- casual_chat: "how are you", "what can you do"
- sql_query: data analysis questions
- forecast: prediction requests
- anomaly: outlier detection
- knowledge_graph: relationship mapping
```

#### New Workflow Nodes:
```
classify_intent
    ↓
[NEW] handle_greeting (if intent=greeting/casual_chat/name_introduction)
    ↓
    END (return friendly response)

OR

generate_sql (if intent=sql_query/forecast/anomaly)
    ↓
    ... (existing workflow)
```

### 4. Memory-Aware Prompts

#### Greeting Handler:
```python
GREETING_PROMPT = """
You are Neural Analytics 2.0, a friendly AI analytics assistant.

User Profile:
{user_profile}

Recent Conversation:
{recent_history}

User said: {message}

Respond naturally and warmly. If you know their name, use it.
If they're introducing themselves, acknowledge it warmly.
Offer help with data analysis.
"""
```

#### SQL Generation with Memory:
```python
SQL_PROMPT_WITH_MEMORY = """
You are a PostgreSQL analyst for {user_name or "the user"}.

Previous Findings:
{key_findings}

Recent Questions:
{recent_questions}

Current Question: {question}

Generate SQL that builds upon previous analysis when relevant.
Reference earlier findings in your explanation.
"""
```

### 5. API Changes

#### Request Model Update:
```python
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # NEW
    table_name: Optional[str] = None
    table_names: Optional[List[str]] = None
```

#### Response Model Update:
```python
{
    "question": "...",
    "session_id": "uuid-string",  # NEW - always returned
    "sql": "...",
    "data": {...},
    "summary": "...",
    "meta": {
        "conversation_turn": 5,  # NEW
        "user_name": "Anubhav",  # NEW (if known)
        ...
    }
}
```

### 6. State Model Updates

```python
class AnalyticsState(TypedDict):
    # Existing fields...
    
    # NEW memory fields
    session_id: Optional[str]
    conversation_history: Optional[List[Dict[str, Any]]]
    user_profile: Optional[Dict[str, Any]]
    key_findings: Optional[List[str]]
    conversation_summary: Optional[str]
```

### 7. Frontend Integration

#### Changes Required:
```javascript
// Store session_id in component state or localStorage
const [sessionId, setSessionId] = useState(
    localStorage.getItem('neural_session_id')
);

// Include in API calls
const response = await fetch('/ask', {
    method: 'POST',
    body: JSON.stringify({
        question: userInput,
        session_id: sessionId,  // NEW
        table_names: selectedTables
    })
});

// Store returned session_id
const data = await response.json();
if (data.session_id && !sessionId) {
    setSessionId(data.session_id);
    localStorage.setItem('neural_session_id', data.session_id);
}
```

### 8. Configuration

#### .env additions:
```bash
# Memory Configuration
MEMORY_BACKEND=hybrid  # Options: memory, redis, hybrid
REDIS_URL=redis://localhost:6379/0  # Optional
SESSION_TTL_HOURS=24
MAX_CONVERSATION_TURNS=50
SUMMARIZE_AFTER_TURNS=5
```

## Implementation Phases

### Phase 1: Core Memory Infrastructure ✓
1. Create memory module structure
2. Implement in-memory session manager
3. Add Redis fallback support
4. Create memory summarizer

### Phase 2: Workflow Integration ✓
1. Update AnalyticsState model
2. Add greeting handler node
3. Update intent classifier
4. Add memory context to prompts

### Phase 3: API Integration ✓
1. Update request/response models
2. Add session management to routes
3. Implement session cleanup

### Phase 4: Frontend Integration ✓
1. Add session_id handling
2. Update API service
3. Store session in localStorage

### Phase 5: Testing & Refinement ✓
1. Test greeting responses
2. Test name memory
3. Test conversation continuity
4. Test cross-referencing

## Example Conversations

### Example 1: Greeting & Introduction
```
User: Hi
Assistant: Hi! How can I help you today? I can analyze your data, create visualizations, detect anomalies, and more.

User: My name is Anubhav
Assistant: Nice to meet you, Anubhav! I'm Neural Analytics 2.0, your AI analytics assistant. What would you like to analyze today?

User: Show me the diagnosis distribution
Assistant: Sure, Anubhav! Let me analyze the diagnosis distribution for you...
[SQL query + results]
```

### Example 2: Context Continuity
```
User: How many malignant cases are there?
Assistant: There are 212 malignant cases in the dataset.
[SQL + data]

User: What about benign?
Assistant: Building on your previous question about malignant cases (212), there are 357 benign cases in the dataset.
[SQL + data]

User: Compare them
Assistant: Based on our earlier findings:
- Malignant: 212 cases (37.3%)
- Benign: 357 cases (62.7%)
[Chart showing comparison]
```

### Example 3: Smart Summarization
```
[After 10+ queries]

User: What have we discovered so far?
Assistant: Great question, Anubhav! Here's what we've analyzed in this session:

Key Findings:
1. Dataset contains 569 total cases (212 malignant, 357 benign)
2. Mean radius ranges from 11.42 to 20.57
3. Malignant tumors show higher compactness values
4. Fractal dimension correlates with diagnosis

Active Tables: user_table_0ddf41f7301f

Would you like to explore any of these findings further?
```

## Benefits

1. **Natural Interaction**: Users can chat naturally without repeating context
2. **Personalization**: System remembers user preferences and names
3. **Efficiency**: No need to re-explain previous queries
4. **Context Awareness**: Answers build upon previous findings
5. **Better UX**: Feels like talking to a knowledgeable assistant

## Technical Considerations

1. **Memory Limits**: Summarize after 5 turns to control token usage
2. **Privacy**: Sessions expire after 24 hours
3. **Scalability**: Hybrid approach allows Redis for production
4. **Fallback**: System works without memory if Redis unavailable
5. **Testing**: Comprehensive tests for all conversation patterns

## Success Metrics

- ✓ Greeting responses work correctly
- ✓ Name memory persists across queries
- ✓ Previous findings referenced in new answers
- ✓ Session management robust and secure
- ✓ No performance degradation with memory enabled