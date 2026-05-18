# Frontend Integration Guide - Conversation Memory

## Overview

This guide shows how to integrate the conversation memory feature into the React frontend.

## Changes Required

### 1. Add Session State Management

**File**: `frontend/src/App.jsx` or `frontend/src/context/DatasetContext.jsx`

```javascript
import { useState, useEffect } from 'react';

function App() {
  // Add session state
  const [sessionId, setSessionId] = useState(() => {
    // Load from localStorage on mount
    return localStorage.getItem('neural_session_id') || null;
  });

  // Save to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('neural_session_id', sessionId);
    }
  }, [sessionId]);

  // ... rest of your app
}
```

### 2. Update API Service

**File**: `frontend/src/services/api.js`

```javascript
// Add session_id to all requests
export const askQuestion = async (question, tableNames = null, sessionId = null) => {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      table_names: tableNames,
      session_id: sessionId,  // NEW: Include session_id
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  
  // Return both data and session_id
  return {
    ...data,
    session_id: data.session_id  // Backend always returns this
  };
};
```

### 3. Update Chat Component

**File**: `frontend/src/components/ChatWindow/ChatWindow.jsx`

```javascript
import { useState } from 'react';
import { askQuestion } from '../../services/api';

function ChatWindow() {
  const [sessionId, setSessionId] = useState(
    localStorage.getItem('neural_session_id')
  );
  const [messages, setMessages] = useState([]);
  const [userName, setUserName] = useState(null);

  const handleSendMessage = async (userMessage) => {
    try {
      // Send message with session_id
      const response = await askQuestion(
        userMessage,
        selectedTables,
        sessionId  // Include current session_id
      );

      // Update session_id if new or changed
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
        localStorage.setItem('neural_session_id', response.session_id);
      }

      // Update user name if provided
      if (response.meta?.user_name && !userName) {
        setUserName(response.meta.user_name);
      }

      // Add to messages
      setMessages([
        ...messages,
        {
          type: 'user',
          content: userMessage,
        },
        {
          type: 'assistant',
          content: response.summary || response.response,
          data: response.data,
          chart: response.chart_spec,
          sql: response.sql,
        },
      ]);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <div className="chat-window">
      {/* Display user name if known */}
      {userName && (
        <div className="user-greeting">
          Welcome back, {userName}! 👋
        </div>
      )}
      
      {/* Messages */}
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} message={msg} />
      ))}
      
      {/* Input */}
      <ChatInput onSend={handleSendMessage} />
    </div>
  );
}
```

### 4. Add Session Reset Button (Optional)

```javascript
function SessionControls() {
  const handleResetSession = () => {
    localStorage.removeItem('neural_session_id');
    setSessionId(null);
    setUserName(null);
    setMessages([]);
    alert('Session reset! Start a new conversation.');
  };

  return (
    <button onClick={handleResetSession} className="reset-session-btn">
      🔄 New Session
    </button>
  );
}
```

### 5. Display Personalized Greetings

```javascript
function WelcomeScreen({ userName }) {
  return (
    <div className="welcome-screen">
      <h1>
        {userName 
          ? `Welcome back, ${userName}!` 
          : 'Welcome to Neural Analytics 2.0'}
      </h1>
      <p>
        {userName
          ? "I remember our previous conversations. How can I help you today?"
          : "Hi! I'm your AI analytics assistant. What would you like to analyze?"}
      </p>
    </div>
  );
}
```

## Complete Example

Here's a complete example integrating all changes:

```javascript
// frontend/src/App.jsx
import { useState, useEffect } from 'react';
import ChatWindow from './components/ChatWindow/ChatWindow';
import { askQuestion } from './services/api';

function App() {
  const [sessionId, setSessionId] = useState(() => 
    localStorage.getItem('neural_session_id')
  );
  const [userName, setUserName] = useState(null);
  const [messages, setMessages] = useState([]);

  // Persist session_id
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('neural_session_id', sessionId);
    }
  }, [sessionId]);

  const handleSendMessage = async (userMessage, tableNames = null) => {
    // Add user message to UI
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    try {
      // Call API with session_id
      const response = await askQuestion(userMessage, tableNames, sessionId);

      // Update session_id if new
      if (response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }

      // Update user name if detected
      if (response.meta?.user_name && !userName) {
        setUserName(response.meta.user_name);
      }

      // Add assistant response
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: response.summary || response.response,
        data: response.data,
        chart: response.chart_spec,
        sql: response.sql,
        timestamp: new Date().toISOString()
      }]);

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  const handleResetSession = () => {
    if (confirm('Start a new session? This will clear your conversation history.')) {
      localStorage.removeItem('neural_session_id');
      setSessionId(null);
      setUserName(null);
      setMessages([]);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>Neural Analytics 2.0</h1>
        {userName && <span className="user-badge">👤 {userName}</span>}
        <button onClick={handleResetSession}>🔄 New Session</button>
      </header>

      <main>
        <ChatWindow 
          messages={messages}
          userName={userName}
          onSendMessage={handleSendMessage}
        />
      </main>
    </div>
  );
}

export default App;
```

## Testing the Integration

### 1. Test Greeting
```javascript
// User types: "Hi"
// Expected: "Hi! How can I help you today?"
// session_id should be generated and stored
```

### 2. Test Name Introduction
```javascript
// User types: "My name is Anubhav"
// Expected: "Nice to meet you, Anubhav! I'm Neural Analytics 2.0..."
// userName state should be updated
// UI should show "Welcome back, Anubhav!"
```

### 3. Test Name Memory
```javascript
// User types: "What can you do?"
// Expected: Response may include "Anubhav" or show personalized greeting
// session_id should remain the same
```

### 4. Test Session Persistence
```javascript
// Refresh the page
// Expected: session_id loaded from localStorage
// Previous conversation context maintained
```

## Styling Suggestions

```css
/* User greeting badge */
.user-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}

/* Welcome message */
.user-greeting {
  background: #f0f9ff;
  border-left: 4px solid #3b82f6;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 8px;
  font-weight: 500;
}

/* Session reset button */
.reset-session-btn {
  background: transparent;
  border: 1px solid #e5e7eb;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-session-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}
```

## Debugging

### Check Session ID
```javascript
console.log('Current session_id:', sessionId);
console.log('Stored session_id:', localStorage.getItem('neural_session_id'));
```

### Monitor API Calls
```javascript
// In api.js
console.log('Sending request with session_id:', sessionId);
console.log('Response session_id:', data.session_id);
```

### Verify Backend
```bash
# Check session stats
curl http://localhost:8000/sessions/stats

# Expected response:
# {
#   "active_sessions": 1,
#   "backend": "hybrid",
#   "ttl_hours": 24
# }
```

## Common Issues

### Issue 1: Session ID Not Persisting
**Solution**: Check localStorage permissions and ensure useEffect is running

### Issue 2: Name Not Showing
**Solution**: Verify `response.meta.user_name` is being extracted correctly

### Issue 3: Session Expires Too Quickly
**Solution**: Adjust `SESSION_TTL_HOURS` in backend `.env`

## Next Steps

1. Implement the changes above
2. Test with the provided test script: `python backend/test_memory_feature.py`
3. Verify in browser DevTools that session_id is being stored
4. Test the complete conversation flow

## Support

If you encounter issues:
1. Check browser console for errors
2. Verify backend is running and accessible
3. Check network tab for API request/response
4. Review backend logs for session management

---

**Happy coding! 🚀**