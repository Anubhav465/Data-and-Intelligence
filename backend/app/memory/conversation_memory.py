# backend/app/memory/conversation_memory.py
"""
Hybrid in-memory/Redis conversation memory manager

Provides session management with:
- Fast in-memory storage (default)
- Optional Redis fallback for persistence
- Automatic session cleanup (TTL: 24 hours)
- Thread-safe operations
"""

import os
import uuid
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import Redis (optional dependency)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class ConversationMemory:
    """
    Manages conversation sessions with hybrid storage.
    
    Storage Strategy:
    - Primary: In-memory dict (fast, O(1) access)
    - Fallback: Redis (optional, for persistence across restarts)
    
    Features:
    - Session TTL: 24 hours (configurable)
    - Auto-cleanup of expired sessions
    - Thread-safe operations
    - Graceful degradation if Redis unavailable
    """
    
    def __init__(
        self,
        backend: str = "hybrid",
        redis_url: str = None,
        session_ttl_hours: int = 24,
        max_conversation_turns: int = 50
    ):
        """
        Initialize conversation memory manager.
        
        Args:
            backend: "memory", "redis", or "hybrid"
            redis_url: Redis connection URL (optional)
            session_ttl_hours: Session expiration time in hours
            max_conversation_turns: Maximum turns to store per session
        """
        self.backend = backend
        self.session_ttl = timedelta(hours=session_ttl_hours)
        self.max_turns = max_conversation_turns
        
        # In-memory storage
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # Redis storage (optional)
        self.redis_client = None
        if backend in ["redis", "hybrid"] and REDIS_AVAILABLE:
            try:
                redis_url = redis_url or os.getenv("REDIS_URL")
                if redis_url:
                    self.redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=2
                    )
                    # Test connection
                    self.redis_client.ping()
                    print(f"[Memory] Redis connected: {redis_url}")
                else:
                    print("[Memory] Redis URL not configured, using in-memory only")
            except Exception as e:
                print(f"[Memory] Redis connection failed: {e}, falling back to in-memory")
                self.redis_client = None
        
        print(f"[Memory] Initialized with backend={backend}, TTL={session_ttl_hours}h")
    
    def create_session(self) -> str:
        """Create a new session and return session_id"""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "user_profile": {},
            "conversation_history": [],
            "key_findings": [],
            "active_tables": [],
            "conversation_summary": None
        }
        
        self._save_session(session_id, session_data)
        print(f"[Memory] Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        if not session_id:
            return None
        
        # Try in-memory first
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                # Check if expired
                last_active = datetime.fromisoformat(session["last_active"])
                if datetime.utcnow() - last_active > self.session_ttl:
                    del self._sessions[session_id]
                    return None
                return session.copy()
        
        # Try Redis if available
        if self.redis_client:
            try:
                data = self.redis_client.get(f"session:{session_id}")
                if data:
                    session = json.loads(data)
                    # Cache in memory
                    with self._lock:
                        self._sessions[session_id] = session
                    return session.copy()
            except Exception as e:
                print(f"[Memory] Redis get error: {e}")
        
        return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Apply updates
        session.update(updates)
        session["last_active"] = datetime.utcnow().isoformat()
        
        self._save_session(session_id, session)
        return True
    
    def add_conversation_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        intent: str = None,
        extracted_facts: Dict[str, Any] = None
    ) -> bool:
        """Add a conversation turn to session history"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        turn = {
            "turn": len(session["conversation_history"]) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "intent": intent,
            "extracted_facts": extracted_facts or {}
        }
        
        session["conversation_history"].append(turn)
        
        # Limit history size
        if len(session["conversation_history"]) > self.max_turns:
            session["conversation_history"] = session["conversation_history"][-self.max_turns:]
        
        # Update user profile with extracted facts
        if extracted_facts:
            if "user_name" in extracted_facts:
                session["user_profile"]["name"] = extracted_facts["user_name"]
            if "preferences" in extracted_facts:
                session["user_profile"].setdefault("preferences", {}).update(
                    extracted_facts["preferences"]
                )
        
        session["last_active"] = datetime.utcnow().isoformat()
        self._save_session(session_id, session)
        return True
    
    def add_key_finding(self, session_id: str, finding: str) -> bool:
        """Add a key finding to session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if finding not in session["key_findings"]:
            session["key_findings"].append(finding)
            # Keep only last 10 findings
            session["key_findings"] = session["key_findings"][-10:]
            self._save_session(session_id, session)
        
        return True
    
    def set_active_tables(self, session_id: str, table_names: List[str]) -> bool:
        """Set active tables for session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["active_tables"] = table_names
        self._save_session(session_id, session)
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        # Remove from memory
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
        
        # Remove from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                print(f"[Memory] Redis delete error: {e}")
        
        print(f"[Memory] Deleted session: {session_id}")
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions, return count of deleted sessions"""
        deleted = 0
        now = datetime.utcnow()
        
        # Cleanup in-memory sessions
        with self._lock:
            expired_ids = []
            for session_id, session in self._sessions.items():
                last_active = datetime.fromisoformat(session["last_active"])
                if now - last_active > self.session_ttl:
                    expired_ids.append(session_id)
            
            for session_id in expired_ids:
                del self._sessions[session_id]
                deleted += 1
        
        if deleted > 0:
            print(f"[Memory] Cleaned up {deleted} expired sessions")
        
        return deleted
    
    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        with self._lock:
            return len(self._sessions)
    
    def _save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session to storage backends"""
        # Save to memory
        with self._lock:
            self._sessions[session_id] = session_data.copy()
        
        # Save to Redis if available
        if self.redis_client:
            try:
                ttl_seconds = int(self.session_ttl.total_seconds())
                self.redis_client.setex(
                    f"session:{session_id}",
                    ttl_seconds,
                    json.dumps(session_data)
                )
            except Exception as e:
                print(f"[Memory] Redis save error: {e}")


# Singleton instance
_memory_manager: Optional[ConversationMemory] = None
_manager_lock = threading.Lock()


def get_memory_manager() -> ConversationMemory:
    """Get or create the global memory manager instance"""
    global _memory_manager
    
    if _memory_manager is None:
        with _manager_lock:
            if _memory_manager is None:
                backend = os.getenv("MEMORY_BACKEND", "hybrid")
                redis_url = os.getenv("REDIS_URL")
                ttl_hours = int(os.getenv("SESSION_TTL_HOURS", "24"))
                max_turns = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))
                
                _memory_manager = ConversationMemory(
                    backend=backend,
                    redis_url=redis_url,
                    session_ttl_hours=ttl_hours,
                    max_conversation_turns=max_turns
                )
    
    return _memory_manager

# Made with Bob
