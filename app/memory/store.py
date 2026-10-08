"""SQLite-backed conversation memory: message history plus per-session state."""
import json
import sqlite3
import threading
from pathlib import Path


class MemoryStore:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                state TEXT NOT NULL
            );
            """
        )

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            self._db.commit()

    def history(self, session_id: str, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def get_state(self, session_id: str) -> dict:
        with self._lock:
            row = self._db.execute(
                "SELECT state FROM session_state WHERE session_id = ?", (session_id,)
            ).fetchone()
        return json.loads(row[0]) if row else {}

    def set_state(self, session_id: str, state: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO session_state (session_id, state) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET state = excluded.state",
                (session_id, json.dumps(state)),
            )
            self._db.commit()
