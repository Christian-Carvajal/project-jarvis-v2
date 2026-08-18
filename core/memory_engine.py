import sqlite3
import json
import time
import os
from typing import List, Dict, Any, Optional

class MemoryEngine:
    """Persistent Dual-Tier Memory Engine using SQLite singleton storage for fast multi-turn context continuity across application restarts."""

    _instance: Optional['MemoryEngine'] = None

    def __new__(cls, db_path: str = "jarvis_memory.db"):
        if cls._instance is None:
            cls._instance = super(MemoryEngine, cls).__new__(cls)
            cls._instance._init_db(db_path)
        return cls._instance

    def _init_db(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    role TEXT,
                    content TEXT,
                    intent TEXT,
                    metadata TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            """)

    def store_turn(self, role: str, content: str, intent: str = "", metadata: Optional[Dict[str, Any]] = None):
        """Stores a single conversation turn asynchronously in SQLite memory."""
        meta_str = json.dumps(metadata or {})
        now = time.time()
        with self.conn:
            self.conn.execute(
                "INSERT INTO conversation_logs (timestamp, role, content, intent, metadata) VALUES (?, ?, ?, ?, ?)",
                (now, role, content, intent, meta_str)
            )

    def get_recent_context(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieves recent conversation turns for LLM prompt context."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content, intent FROM conversation_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        result = []
        for r in reversed(rows):
            result.append({"role": r["role"], "content": r["content"], "intent": r["intent"]})
        return result

    def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Keyword & semantic context search over historical conversations."""
        clean_q = query.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM conversation_logs WHERE LOWER(content) LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{clean_q}%", limit)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]

    def set_preference(self, key: str, value: str):
        """Sets a persistent user preference key-value pair."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, time.time())
            )

    def get_preference(self, key: str) -> Optional[str]:
        """Gets a persistent user preference value."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None
