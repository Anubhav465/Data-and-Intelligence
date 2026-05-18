# Memory System Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  User Input: "Hi, my name is Anubhav"                        │  │
│  │  Session ID: stored in localStorage or state                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ POST /ask
                             │ { question, session_id?, table_names? }
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API LAYER (routes.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  1. Extract/Generate session_id                              │  │
│  │  2. Retrieve conversation history from memory                │  │
│  │  3. Pass to workflow with context                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MEMORY LAYER (app/memory/)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ConversationMemory (conversation_memory.py)                 │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  In-Memory Store (Dict)                                │  │  │
│  │  │  {                                                      │  │  │
│  │  │    "session_123": {                                    │  │  │
│  │  │      "user_profile": {"name": "Anubhav"},             │  │  │
│  │  │      "conversation_history": [...],                   │  │  │
│  │  │      "key_findings": [...],                           │  │  │
│  │  │      "last_active": "2026-05-18T15:45:00Z"           │  │  │
│  │  │    }                                                   │  │  │
│  │  │  }                                                      │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                           ↕                                   │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  Redis Fallback (Optional)                            │  │  │
│  │  │  - Persistence across restarts                        │  │  │
│  │  │  - Distributed sessions                               │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  MemorySummarizer (memory_summarizer.py)                    │  │
│  │  - Summarize conversations after 5 turns                    │  │
│  │  - Extract key facts (name, preferences, findings)          │  │
│  │  - Keep recent 5 turns + summary of older                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH WORKFLOW (workflow.py)                   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  classify_intent                                             │  │
│  │  - greeting / name_introduction / casual_chat / sql_query    │  │
│  └────────────┬─────────────────────────────────┬───────────────┘  │
│               │                                 │                   │
│               ▼                                 ▼                   │
│  ┌────────────────────────┐      ┌──────────────────────────────┐  │
│  │  handle_greeting       │      │  generate_sql                │  │
│  │  (NEW NODE)            │      │  (with memory context)       │  │
│  │                        │      │                              │  │
│  │  - Use user name       │      │  Prompt includes:            │  │
│  │  - Reference history   │      │  - User name                 │  │
│  │  - Warm response       │      │  - Previous findings         │  │
│  │  - Offer help          │      │  - Recent questions          │  │
│  └────────────┬───────────┘      └──────────────┬───────────────┘  │
│               │                                 │                   │
│               ▼                                 ▼                   │
│  ┌────────────────────────┐      ┌──────────────────────────────┐  │
│  │  build_response        │      │  execute_query               │  │
│  │  - Add session_id      │      │  ...                         │  │
│  │  - Add user_name       │      │  (existing workflow)         │  │
│  └────────────────────────┘      └──────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MEMORY UPDATE (routes.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  1. Store conversation turn in memory                        │  │
│  │  2. Extract facts (name, preferences, findings)              │  │
│  │  3. Update user profile                                      │  │
│  │  4. Trigger summarization if needed (>5 turns)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           RESPONSE                                   │
│  {                                                                   │
│    "question": "Hi, my name is Anubhav",                            │
│    "session_id": "uuid-123",                                        │
│    "response": "Nice to meet you, Anubhav! I'm Neural Analytics...",│
│    "meta": {                                                         │
│      "conversation_turn": 2,                                        │
│      "user_name": "Anubhav"                                         │
│    }                                                                 │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Intent Classification Flow

```
User Input
    ↓
┌─────────────────────────────────────────┐
│  Intent Classifier (LLM)                │
│                                         │
│  Patterns:                              │
│  - "hi", "hello", "hey"                 │
│    → greeting                           │
│                                         │
│  - "my name is X", "I'm X"              │
│    → name_introduction                  │
│                                         │
│  - "how are you", "what can you do"     │
│    → casual_chat                        │
│                                         │
│  - "show me X", "analyze Y"             │
│    → sql_query                          │
│                                         │
│  - "predict", "forecast"                │
│    → forecast                           │
│                                         │
│  - "anomaly", "outlier"                 │
│    → anomaly                            │
└─────────────────────────────────────────┘
    ↓
Route to appropriate handler
```

## Memory Summarization Strategy

```
Conversation Timeline:
┌─────────────────────────────────────────────────────────────────┐
│  Turn 1-5: Full History (Recent)                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Turn 1: "Hi" → "Hi! How can I help?"                      │ │
│  │ Turn 2: "My name is Anubhav" → "Nice to meet you..."      │ │
│  │ Turn 3: "Show diagnosis" → [SQL + Results]                │ │
│  │ Turn 4: "What about benign?" → [SQL + Results]            │ │
│  │ Turn 5: "Compare them" → [SQL + Chart]                    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    (After Turn 6+)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Summarized History (Older)                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Summary: "User Anubhav analyzed diagnosis distribution.   │ │
│  │ Found 212 malignant and 357 benign cases. Compared        │ │
│  │ characteristics between groups."                          │ │
│  │                                                            │ │
│  │ Key Facts Extracted:                                      │ │
│  │ - User name: Anubhav                                      │ │
│  │ - Active table: user_table_0ddf41f7301f                   │ │
│  │ - Key finding: 212 malignant, 357 benign                  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            +
┌─────────────────────────────────────────────────────────────────┐
│  Turn 6-10: Full History (Recent)                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Turn 6: "Show mean radius" → [SQL + Results]              │ │
│  │ Turn 7: "Any outliers?" → [Anomaly Detection]             │ │
│  │ Turn 8: "Create knowledge graph" → [Graph]                │ │
│  │ Turn 9: "Forecast trends" → [Forecast]                    │ │
│  │ Turn 10: "Summarize findings" → [Summary]                 │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Session Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│  Session Creation                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  1. User sends first message (no session_id)               │  │
│  │  2. Backend generates UUID: "session_abc123"               │  │
│  │  3. Initialize session data structure                      │  │
│  │  4. Return session_id in response                          │  │
│  │  5. Frontend stores in localStorage                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  Active Session (TTL: 24 hours)                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  - Each request includes session_id                        │  │
│  │  - Memory retrieved and updated                            │  │
│  │  - last_active timestamp refreshed                         │  │
│  │  - Conversation history grows                              │  │
│  │  - Summarization triggered after 5 turns                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  Session Expiration                                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  - Background cleanup task runs every hour                 │  │
│  │  - Check last_active timestamp                             │  │
│  │  - Delete sessions older than 24 hours                     │  │
│  │  - Free memory / Redis storage                             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Example: "Hi, my name is Anubhav"

```
1. Frontend → Backend
   POST /ask
   {
     "question": "Hi, my name is Anubhav",
     "session_id": null  // First message
   }

2. API Layer
   - No session_id → Generate new: "session_abc123"
   - Initialize empty conversation history
   - Pass to workflow

3. Workflow: classify_intent
   - LLM detects: "name_introduction"
   - Route to: handle_greeting node

4. Workflow: handle_greeting
   - Extract name: "Anubhav"
   - Generate warm response using memory_prompts
   - Response: "Nice to meet you, Anubhav! I'm Neural Analytics 2.0..."

5. Memory Update
   - Store conversation turn:
     {
       "turn": 1,
       "user_message": "Hi, my name is Anubhav",
       "assistant_response": "Nice to meet you...",
       "intent": "name_introduction",
       "extracted_facts": {"user_name": "Anubhav"}
     }
   - Update user_profile: {"name": "Anubhav"}

6. Backend → Frontend
   {
     "question": "Hi, my name is Anubhav",
     "session_id": "session_abc123",  // NEW session
     "response": "Nice to meet you, Anubhav! I'm Neural Analytics 2.0...",
     "meta": {
       "conversation_turn": 1,
       "user_name": "Anubhav",
       "intent": "name_introduction"
     }
   }

7. Frontend
   - Store session_id in localStorage
   - Display response
   - Include session_id in all future requests
```

## Memory Context Injection

### For SQL Queries:
```python
# Before (no memory):
prompt = f"Generate SQL for: {question}"

# After (with memory):
prompt = f"""
Generate SQL for {user_name or 'the user'}.

Previous Findings:
{format_key_findings(memory.key_findings)}

Recent Questions:
{format_recent_questions(memory.conversation_history[-3:])}

Current Question: {question}

Build upon previous analysis when relevant.
"""
```

### For Greetings:
```python
# Before (no memory):
response = "Hi! How can I help you today?"

# After (with memory):
if user_name:
    response = f"Hi {user_name}! How can I help you today?"
    
if previous_findings:
    response += f"\n\nLast time we analyzed: {previous_findings[0]}"
```

## Benefits Summary

1. **Natural Conversations**: Users can chat like with a human
2. **Personalization**: System remembers names and preferences
3. **Context Continuity**: No need to repeat information
4. **Efficient Analysis**: Build upon previous findings
5. **Better UX**: Feels intelligent and attentive

## Implementation Priority

**Phase 1 (Core)**: ✓ Must have for basic memory
- In-memory session storage
- Session ID generation
- Basic greeting handling
- Name extraction and storage

**Phase 2 (Enhanced)**: ✓ Important for good UX
- Conversation history tracking
- Context injection in SQL prompts
- Cross-referencing previous findings

**Phase 3 (Advanced)**: Optional but valuable
- Redis persistence
- Smart summarization
- Advanced fact extraction
- Session analytics