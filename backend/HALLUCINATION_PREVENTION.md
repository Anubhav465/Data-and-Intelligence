# 🚫 Hallucination Prevention Guide

## Overview

The Neural Analytics system now includes **out-of-scope detection** to prevent hallucination. When users ask questions outside the data analytics domain (like "What's the weather?"), the system politely rejects them instead of generating false or irrelevant answers.

---

## 🎯 Problem Solved

**Before**: If a user uploaded a breast cancer dataset and asked "What's the weather today?", the system might try to generate SQL or provide irrelevant responses.

**After**: The system detects the question is out-of-scope, politely explains it can only help with data analytics, and offers to analyze the uploaded data instead.

---

## 🔍 How It Works

### 1. Intent Classification Enhancement

The intent classifier now includes an `out_of_scope` intent type:

```python
class IntentClassification(BaseModel):
    intent: str  # Can be: greeting, sql_query, forecast, anomaly, 
                 # knowledge_graph, summary, or out_of_scope
    is_out_of_scope: bool
    rejection_reason: Optional[str]
```

### 2. Smart Detection

The classifier analyzes questions against these categories:

**OUT OF SCOPE** (rejected):
- Weather queries: "What's the weather today?"
- Sports questions: "Who won the game?"
- General knowledge: "What's the capital of France?"
- News: "What are the latest headlines?"
- Cooking: "How do I make pasta?"
- History: "Tell me about World War II"

**IN SCOPE** (accepted):
- Data analysis: "Show me sales trends"
- Anomaly detection: "Find outliers in my data"
- Forecasting: "Predict next month's revenue"
- Summaries: "What's in my dataset?"
- Knowledge graphs: "Build a feature correlation graph"

### 3. Context-Aware Detection

The system considers available datasets:

```python
# If user has uploaded breast cancer data
data_context = "Available datasets: user_table_breast_cancer"

# Classifier knows the domain and rejects irrelevant questions
```

### 4. Polite Rejection Responses

When an out-of-scope question is detected, the system:

1. **Acknowledges the user** (uses their name if known)
2. **Explains the limitation** politely
3. **Describes capabilities** (what it CAN do)
4. **Offers alternatives** (suggests analyzing their data)

Example response:
```
I'm sorry Anubhav, but I can only help with data analytics questions. 
I specialize in analyzing your uploaded datasets, creating visualizations, 
detecting anomalies, and forecasting trends. Would you like to explore 
your breast cancer data instead?
```

---

## 🛠️ Implementation Details

### Modified Files

1. **`backend/app/models/state.py`**
   - Added `is_out_of_scope` and `rejection_reason` to `IntentClassification`

2. **`backend/app/memory/memory_prompts.py`**
   - Added `OUT_OF_SCOPE_PROMPT` template
   - Added `get_out_of_scope_prompt()` function

3. **`backend/app/graph/workflow.py`**
   - Enhanced intent classifier with out-of-scope detection
   - Added out-of-scope handling in `handle_greeting_node()`
   - Updated routing to handle `out_of_scope` intent

4. **`backend/app/memory/__init__.py`**
   - Exported `get_out_of_scope_prompt`

---

## 🧪 Testing

### Run the Test Suite

```bash
cd backend
python test_hallucination_prevention.py
```

### Test Cases

The test suite validates:

**Out-of-Scope Detection** (should reject):
- ✅ Weather questions
- ✅ Sports questions
- ✅ History questions
- ✅ Cooking questions
- ✅ Geography questions
- ✅ News questions

**In-Scope Detection** (should accept):
- ✅ Data analysis questions
- ✅ Anomaly detection requests
- ✅ Forecasting queries
- ✅ Summary requests

**Response Quality**:
- ✅ Mentions user name (personalized)
- ✅ Polite and apologetic tone
- ✅ Explains system limitations
- ✅ Offers helpful alternatives

---

## 📊 Example Scenarios

### Scenario 1: Weather Question

**User**: "What's the weather today?"

**System Response**:
```
I'm sorry, but I can only help with data analytics questions. 
I specialize in analyzing your uploaded datasets, creating 
visualizations, detecting anomalies, and forecasting trends. 
Would you like to explore your data instead?
```

**Intent**: `out_of_scope`  
**Rejection Reason**: "Question about weather, outside analytics domain"

---

### Scenario 2: Sports Question

**User**: "Who won the football game last night?"

**System Response**:
```
I'm sorry Anubhav, but I cannot answer questions about sports. 
I focus on data analytics - analyzing your datasets, creating 
charts, detecting anomalies, and forecasting trends. Would you 
like to analyze your breast cancer data instead?
```

**Intent**: `out_of_scope`  
**Rejection Reason**: "Question about sports, outside analytics domain"

---

### Scenario 3: Valid Data Question

**User**: "Show me the correlation between tumor size and diagnosis"

**System Response**:
```sql
-- Generates appropriate SQL query
SELECT 
    diagnosis,
    AVG(radius_mean) as avg_radius,
    AVG(texture_mean) as avg_texture,
    COUNT(*) as count
FROM uploads."user_table_breast_cancer"
GROUP BY diagnosis;
```

**Intent**: `sql_query`  
**Action**: Proceeds with normal analytics workflow

---

## 🎨 Customization

### Adjust Detection Sensitivity

Edit the intent classifier prompt in `backend/app/graph/workflow.py`:

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intent classifier for a DATA ANALYTICS system.

IMPORTANT: This system ONLY handles data analysis questions.

OUT OF SCOPE EXAMPLES:
- "What's the weather today?" → out_of_scope (weather)
- "Who won the game?" → out_of_scope (sports)
# Add more examples here...

IN SCOPE EXAMPLES:
- "Show me sales trends" → sql_query
# Add more examples here...
""")
])
```

### Customize Rejection Messages

Edit `OUT_OF_SCOPE_PROMPT` in `backend/app/memory/memory_prompts.py`:

```python
OUT_OF_SCOPE_PROMPT = """You are Neural Analytics 2.0, an AI analytics assistant.

User asked: {message}

This question is outside your domain. You specialize in:
- Data analysis and SQL queries
- Chart and visualization creation
- Anomaly detection in datasets
- Time-series forecasting
- Knowledge graph generation
- Statistical analysis

Politely explain that you cannot answer questions about {topic}.
Offer to help with their uploaded data instead.
"""
```

---

## 🔧 Configuration

No additional configuration needed! The feature works out-of-the-box with your existing setup.

### Optional: Adjust LLM Temperature

For stricter classification, reduce temperature in `workflow.py`:

```python
self.intent_llm = ChatOpenAI(
    model="gpt-4-turbo-preview",
    temperature=0.0,  # Already at 0 for deterministic classification
    api_key=os.getenv("OPENAI_API_KEY", "")
)
```

---

## 📈 Benefits

1. **Prevents Hallucination**: No false answers about weather, sports, etc.
2. **User Education**: Teaches users what the system can do
3. **Better UX**: Polite, helpful responses instead of errors
4. **Domain Focus**: Keeps conversations on-topic (data analytics)
5. **Personalized**: Uses user names for friendly interactions

---

## 🚀 Integration with Existing Features

### Works With Memory System

```python
# If user previously introduced themselves
user_profile = {"name": "Anubhav"}

# Rejection response will be personalized
"I'm sorry Anubhav, but I can only help with data analytics..."
```

### Works With Session Management

```python
# Out-of-scope questions are logged in conversation history
memory.add_conversation_turn(
    session_id=session_id,
    user_message="What's the weather?",
    assistant_response="I'm sorry, but I can only help with...",
    intent="out_of_scope"
)
```

### Works With Multi-Table Uploads

```python
# System knows what data is available
table_names = ["sales_data", "customer_data"]

# Rejection mentions available datasets
"Would you like to analyze your sales_data or customer_data instead?"
```

---

## 🐛 Troubleshooting

### Issue: Valid questions rejected

**Solution**: Add more in-scope examples to the classifier prompt

### Issue: Invalid questions accepted

**Solution**: Add more out-of-scope examples to the classifier prompt

### Issue: Generic rejection messages

**Solution**: Enhance topic detection in `handle_greeting_node()`:

```python
# Add more topic keywords
if any(word in question_lower for word in ["weather", "temperature", "forecast"]):
    topic = "weather forecasting"  # More specific
```

---

## 📚 Related Documentation

- [Memory Feature Guide](./MEMORY_FEATURE_README.md)
- [Quick Start Guide](./QUICK_START_MEMORY.md)
- [Architecture Overview](./MEMORY_ARCHITECTURE.md)
- [Frontend Integration](../frontend/MEMORY_INTEGRATION_GUIDE.md)

---

## ✅ Checklist

Before deploying:

- [ ] Run `python test_hallucination_prevention.py`
- [ ] Verify all tests pass
- [ ] Test with real user questions
- [ ] Customize rejection messages if needed
- [ ] Update frontend to display rejection responses
- [ ] Monitor logs for false positives/negatives

---

## 🎯 Success Metrics

Track these metrics to measure effectiveness:

1. **Out-of-Scope Detection Rate**: % of irrelevant questions caught
2. **False Positive Rate**: % of valid questions incorrectly rejected
3. **User Satisfaction**: Feedback on rejection responses
4. **Conversation Quality**: Fewer confused/frustrated users

---

## 🔮 Future Enhancements

Potential improvements:

1. **Domain Expansion**: Support more analytics domains (finance, healthcare, etc.)
2. **Smart Suggestions**: Recommend similar in-scope questions
3. **Learning System**: Improve detection based on user feedback
4. **Multi-Language**: Support rejection messages in multiple languages

---

**Made with ❤️ by Bob**

*Last Updated: 2026-05-18*