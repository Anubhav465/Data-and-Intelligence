# Quick Start Guide - Conversation Memory Feature

## 🚀 Get Started in 5 Minutes

### Step 1: Configure Environment

```bash
cd backend

# Copy the memory configuration template
cp .env.memory.example .env

# Edit .env and set your API keys
# Required:
OPENAI_API_KEY=your_openai_key_here
COHERE_API_KEY=your_cohere_key_here

# Optional (for Redis persistence):
REDIS_URL=redis://localhost:6379/0
```

### Step 2: Install Dependencies (if needed)

```bash
# The memory feature uses existing dependencies
# But if you need Redis support:
pip install redis
```

### Step 3: Start the Backend

```bash
# From backend directory
python main_langchain.py

# Or with uvicorn
uvicorn main_langchain:app --reload --port 8000
```

### Step 4: Test the Feature

```bash
# Run the test script
python test_memory_feature.py
```

Expected output:
```
🧪 🧪 🧪 ... CONVERSATION MEMORY FEATURE - TEST SUITE

============================================================
  TEST 1: Greeting Response
============================================================

Session ID: abc-123-def-456
Intent: greeting
Response: Hi! How can I help you today? I can analyze your data...

✅ Test 1 PASSED: Greeting response works correctly

============================================================
  TEST 2: Name Introduction
============================================================

Session ID: abc-123-def-456
Intent: name_introduction
Response: Nice to meet you, Anubhav! I'm Neural Analytics 2.0...

✅ Test 2 PASSED: Name introduction works correctly

... (more tests)

============================================================
  🎉 ALL TESTS PASSED!
============================================================
```

### Step 5: Try It Manually

```bash
# Test 1: Greeting
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hi"}'

# Save the session_id from the response

# Test 2: Introduce yourself
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "My name is Anubhav",
    "session_id": "YOUR_SESSION_ID_HERE"
  }'

# Test 3: Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What can you do?",
    "session_id": "YOUR_SESSION_ID_HERE"
  }'
```

## 📊 Check Session Stats

```bash
curl http://localhost:8000/sessions/stats
```

Response:
```json
{
  "active_sessions": 1,
  "backend": "hybrid",
  "ttl_hours": 24
}
```

## 🎯 Example Conversation

```
User: Hi
Bot: Hi! How can I help you today? I can analyze your data, create 
visualizations, detect anomalies, and more.

User: My name is Anubhav
Bot: Nice to meet you, Anubhav! I'm Neural Analytics 2.0, your AI 
analytics assistant. What would you like to analyze today?

User: Show me the top 5 products
Bot: Sure, Anubhav! Let me analyze the top 5 products for you...
[SQL query + results + chart]

User: What about the bottom 5?
Bot: Building on your previous query about top products, here are 
the bottom 5 products...
[SQL query + results]
```

## 🔧 Configuration Options

Edit `.env` to customize:

```bash
# Memory backend
MEMORY_BACKEND=hybrid  # Options: memory, redis, hybrid

# Session settings
SESSION_TTL_HOURS=24           # How long sessions last
MAX_CONVERSATION_TURNS=50      # Max turns to store
SUMMARIZE_AFTER_TURNS=5        # When to summarize

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

## 🐛 Troubleshooting

### Issue: "Cannot connect to server"
**Solution**: Make sure backend is running on port 8000

### Issue: "Session not persisting"
**Solution**: Check that MEMORY_BACKEND is set correctly in .env

### Issue: "Name not being remembered"
**Solution**: Verify session_id is being passed in subsequent requests

### Issue: "Redis connection failed"
**Solution**: Either install/start Redis, or set MEMORY_BACKEND=memory

## 📚 Next Steps

1. ✅ Backend is working - Test with `test_memory_feature.py`
2. 📱 Integrate frontend - See `frontend/MEMORY_INTEGRATION_GUIDE.md`
3. 🎨 Customize prompts - Edit `backend/app/memory/memory_prompts.py`
4. ⚙️ Tune settings - Adjust `.env` configuration

## 🎉 You're Ready!

The conversation memory feature is now active. Your assistant will:
- Remember user names
- Maintain conversation context
- Respond naturally to greetings
- Reference previous findings
- Provide personalized responses

## 📖 Full Documentation

- **Feature Overview**: `MEMORY_FEATURE_README.md`
- **Implementation Details**: `MEMORY_IMPLEMENTATION_PLAN.md`
- **Architecture**: `MEMORY_ARCHITECTURE.md`
- **Frontend Guide**: `../frontend/MEMORY_INTEGRATION_GUIDE.md`

---

**Need help?** Check the documentation or review the test script for examples.

**Happy analyzing! 🚀**