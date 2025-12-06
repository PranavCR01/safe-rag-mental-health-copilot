# core/persistent_memory.py

"""
Persistent conversation memory using SQLite instead of in-memory only.
This ensures context is maintained even after server restarts.
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

DB_PATH = "storage/conversation_memory.sqlite"

def init_memory_db():
    """Initialize the persistent memory database"""
    os.makedirs("storage", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,  -- 'user' or 'assistant'
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    """)
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
    session_id: Optional[str] = None
):
    """
    Save a single conversation turn to persistent storage
    
    Args:
        user_id: Unique user identifier
        role: 'user' or 'assistant'
        message: The message content
        session_id: Optional session grouping
    """
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO conversation_turns (user_id, role, message, session_id) VALUES (?, ?, ?, ?)",
        (user_id, role, message, session_id)
    )
    con.commit()
    con.close()


def get_conversation_history(
    user_id: str,
    limit: int = 10,
    hours_back: int = 24
) -> List[Dict[str, str]]:
    """
    Retrieve recent conversation history for a user
    
    Args:
        user_id: User to get history for
        limit: Maximum number of turns to retrieve
        hours_back: Only get messages from the last N hours
    
    Returns:
        List of conversation turns, each with 'role' and 'message'
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    cursor = con.execute("""
        SELECT role, message, created_at
        FROM conversation_turns
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (user_id, cutoff_time.isoformat(), limit))
    
    rows = cursor.fetchall()
    con.close()
    
    # Reverse to get chronological order (oldest first)
    # Already in chronological order, no need to reverse
    history = [{"role": row["role"], "message": row["message"]} for row in rows]
    
    return history


def format_conversation_context(history: List[Dict[str, str]]) -> str:
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
    
    # Simple summary: Last few turns
    summary_parts = []
    char_count = 0
    
    for turn in reversed(history):  # Start from most recent
        line = f"{turn['role']}: {turn['message']}"
        if char_count + len(line) > max_chars:
            break
        summary_parts.insert(0, line)
        char_count += len(line)
    
    return "\n".join(summary_parts)


def clear_old_conversations(days_old: int = 30):
    """
    Clear conversations older than N days (privacy/cleanup)
    
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
    
    Returns:
        Dictionary with conversation stats
    """
    con = sqlite3.connect(DB_PATH)
    
    # Total turns
    cursor = con.execute(
        "SELECT COUNT(*) as count FROM conversation_turns WHERE user_id = ?",
        (user_id,)
    )
    total_turns = cursor.fetchone()[0]
    
    # First conversation
    cursor = con.execute(
        "SELECT created_at FROM conversation_turns WHERE user_id = ? ORDER BY created_at ASC LIMIT 1",
        (user_id,)
    )
    first_turn = cursor.fetchone()
    first_date = first_turn[0] if first_turn else None
    
    # Last conversation
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

def save_chat_turn(user_id: str, user_message: str, assistant_message: str):
    """
    Convenience function to save both user and assistant messages
    
    Args:
        user_id: User identifier
        user_message: What the user said
        assistant_message: What the assistant replied
    """
    save_conversation_turn(user_id, "user", user_message)
    save_conversation_turn(user_id, "assistant", assistant_message)


def load_context_for_compose(user_id: str, format_type: str = "full") -> str:
    """
    Load conversation context in format suitable for compose()
    
    Args:
        user_id: User to load context for
        format_type: 'full' or 'summary'
    
    Returns:
        Formatted context string
    """
    if format_type == "summary":
        return get_conversation_summary(user_id, max_chars=500)
    else:
        history = get_conversation_history(user_id, limit=6)  # Last 3 exchanges
        return format_conversation_context(history)


# ===== TESTING =====

if __name__ == "__main__":
    print("Testing Persistent Memory System...\n")
    
    # Test user
    test_user = "test_user_123"
    
    # Save some conversation turns
    print("1. Saving conversation turns...")
    save_chat_turn(
        test_user,
        "I'm really stressed about my exam tomorrow",
        "I understand. Let's work through this together. What subject is the exam?"
    )
    save_chat_turn(
        test_user,
        "It's for calculus",
        "Calculus can be challenging. What topics are you most worried about?"
    )
    
    # Retrieve history
    print("\n2. Retrieving conversation history...")
    history = get_conversation_history(test_user, limit=10)
    for turn in history:
        print(f"  {turn['role']}: {turn['message'][:50]}...")
    
    # Get formatted context
    print("\n3. Formatted context for LLM:")
    context = load_context_for_compose(test_user)
    print(context)
    
    # Get stats
    print("\n4. User conversation stats:")
    stats = get_user_conversation_stats(test_user)
    print(f"  Total turns: {stats['total_turns']}")
    print(f"  First conversation: {stats['first_conversation']}")
    print(f"  Last conversation: {stats['last_conversation']}")
    
    print("\n✅ Persistent memory working!")