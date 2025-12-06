# 

# core/persistent_memory.py

"""
Persistent conversation memory using SQLite with metadata support.
Saves analysis data (tier, confidence, citations) along with messages.
"""

import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import os
import json
import time

DB_PATH = "storage/conversation_memory.sqlite"

def init_memory_db():
    """Initialize the persistent memory database with metadata column"""
    os.makedirs("storage", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    
    # Create main table
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    """)
    
    # Add metadata column if it doesn't exist (for existing databases)
    try:
        con.execute("ALTER TABLE conversation_turns ADD COLUMN metadata TEXT")
    except:
        pass  # Column already exists
    
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_id ON conversation_turns(user_id)
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at ON conversation_turns(created_at)
    """)
    con.commit()
    con.close()

# Initialize on import
init_memory_db()


def save_conversation_turn(
    user_id: str,
    role: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
):
    """
    Save a single conversation turn with optional metadata
    
    Args:
        user_id: Unique user identifier
        role: 'user' or 'assistant'
        message: The message content
        metadata: Optional dict with analysis data, citations, etc.
        session_id: Optional session grouping
    """
    con = sqlite3.connect(DB_PATH)
    
    # Convert metadata to JSON string
    metadata_json = json.dumps(metadata) if metadata else None
    
    con.execute(
        "INSERT INTO conversation_turns (user_id, role, message, metadata, session_id) VALUES (?, ?, ?, ?, ?)",
        (user_id, role, message, metadata_json, session_id)
    )
    con.commit()
    con.close()


def get_conversation_history(
    user_id: str,
    limit: int = 10,
    hours_back: int = 24
) -> List[Dict[str, Any]]:
    """
    Retrieve recent conversation history with metadata
    
    Args:
        user_id: User to get history for
        limit: Maximum number of turns to retrieve
        hours_back: Only get messages from the last N hours
    
    Returns:
        List of conversation turns with 'role', 'message', and 'metadata'
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    # Get messages in chronological order
    cursor = con.execute("""
        SELECT role, message, metadata, created_at
        FROM conversation_turns
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (user_id, cutoff_time.isoformat(), limit))
    
    rows = cursor.fetchall()
    con.close()
    
    # Parse metadata from JSON
    history = []
    for row in rows:
        turn = {
            "role": row["role"],
            "message": row["message"]
        }
        
        # Parse metadata if it exists
        if row["metadata"]:
            try:
                turn["metadata"] = json.loads(row["metadata"])
            except:
                pass
        
        history.append(turn)
    
    return history


def format_conversation_context(history: List[Dict[str, Any]]) -> str:
    """
    Format conversation history into a readable context string
    
    Args:
        history: List of conversation turns
    
    Returns:
        Formatted string for LLM context
    """
    if not history:
        return "(No previous conversation)"
    
    formatted = []
    for turn in history:
        role = turn["role"].capitalize()
        message = turn["message"][:200]  # Limit length
        formatted.append(f"{role}: {message}")
    
    return "\n".join(formatted)


def get_conversation_summary(user_id: str, max_chars: int = 500) -> str:
    """
    Get a brief summary of recent conversation
    
    Args:
        user_id: User to summarize for
        max_chars: Maximum characters in summary
    
    Returns:
        Brief summary of conversation topics
    """
    history = get_conversation_history(user_id, limit=10)
    
    if not history:
        return "(No previous conversation)"
    
    summary_parts = []
    char_count = 0
    
    for turn in reversed(history):
        line = f"{turn['role']}: {turn['message']}"
        if char_count + len(line) > max_chars:
            break
        summary_parts.insert(0, line)
        char_count += len(line)
    
    return "\n".join(summary_parts)


def clear_old_conversations(days_old: int = 30):
    """
    Clear conversations older than N days
    
    Args:
        days_old: Delete conversations older than this many days
    """
    con = sqlite3.connect(DB_PATH)
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    con.execute(
        "DELETE FROM conversation_turns WHERE created_at < ?",
        (cutoff_date.isoformat(),)
    )
    
    deleted_count = con.total_changes
    con.commit()
    con.close()
    
    return deleted_count


def get_user_conversation_stats(user_id: str) -> Dict:
    """
    Get statistics about a user's conversation history
    """
    con = sqlite3.connect(DB_PATH)
    
    cursor = con.execute(
        "SELECT COUNT(*) as count FROM conversation_turns WHERE user_id = ?",
        (user_id,)
    )
    total_turns = cursor.fetchone()[0]
    
    cursor = con.execute(
        "SELECT created_at FROM conversation_turns WHERE user_id = ? ORDER BY created_at ASC LIMIT 1",
        (user_id,)
    )
    first_turn = cursor.fetchone()
    first_date = first_turn[0] if first_turn else None
    
    cursor = con.execute(
        "SELECT created_at FROM conversation_turns WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    last_turn = cursor.fetchone()
    last_date = last_turn[0] if last_turn else None
    
    con.close()
    
    return {
        "total_turns": total_turns,
        "first_conversation": first_date,
        "last_conversation": last_date,
        "user_id": user_id
    }


# ===== INTEGRATION HELPERS =====

def save_chat_turn(
    user_id: str, 
    user_message: str, 
    assistant_message: str,
    assistant_metadata: Optional[Dict[str, Any]] = None
):
    """
    Save both user and assistant messages with optional metadata
    
    Args:
        user_id: User identifier
        user_message: What the user said
        assistant_message: What the assistant replied
        assistant_metadata: Optional dict with analysis, citations, etc.
    """
    # Save user message (no metadata)
    save_conversation_turn(user_id, "user", user_message, metadata=None)
    
    # Small delay for timestamp ordering
    time.sleep(0.01)
    
    # Save assistant message with metadata
    save_conversation_turn(user_id, "assistant", assistant_message, metadata=assistant_metadata)


def load_context_for_compose(user_id: str, format_type: str = "full") -> str:
    """
    Load conversation context for LLM
    
    Args:
        user_id: User to load context for
        format_type: 'full' or 'summary'
    
    Returns:
        Formatted context string
    """
    if format_type == "summary":
        return get_conversation_summary(user_id, max_chars=500)
    else:
        history = get_conversation_history(user_id, limit=6)
        return format_conversation_context(history)


# ===== TESTING =====

if __name__ == "__main__":
    print("Testing Persistent Memory with Metadata...\n")
    
    test_user = "test_user_metadata"
    
    # Save conversation with metadata
    print("1. Saving conversation with metadata...")
    save_chat_turn(
        test_user,
        "I'm stressed about my exam",
        "I understand. Let's work through this together.",
        assistant_metadata={
            "tier": 1,
            "confidence": 0.85,
            "citations": [{"source_id": "APA_anxiety", "url": "https://example.com"}],
            "tone_analysis": {"empathy_level": 2, "template": "supportive"}
        }
    )
    
    # Retrieve and check metadata
    print("\n2. Retrieving conversation with metadata...")
    history = get_conversation_history(test_user, limit=10, hours_back=24*7)
    
    for i, turn in enumerate(history):
        print(f"\n  Turn {i+1}:")
        print(f"    Role: {turn['role']}")
        print(f"    Message: {turn['message'][:50]}...")
        if 'metadata' in turn:
            print(f"    Metadata: {turn['metadata']}")
    
    print("\n✅ Persistent memory with metadata working!")