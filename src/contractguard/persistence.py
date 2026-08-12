"""Durable SQLite checkpointing for pause/resume and restart recovery."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any


class SQLiteCheckpointer:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT PRIMARY KEY,
                node TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoint_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                node TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkpoint_history_thread ON checkpoint_history(thread_id, id)"
        )
        self._conn.commit()

    def save(self, thread_id: str, node: str, state: dict[str, Any]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        state["updated_at"] = timestamp
        state["workflow_node"] = node
        payload = json.dumps(state, ensure_ascii=False, default=str)
        status = str(state.get("status", node))
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO checkpoints(thread_id, node, status, payload, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    node=excluded.node,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (thread_id, node, status, payload, timestamp),
            )
            self._conn.execute(
                """
                INSERT INTO checkpoint_history(thread_id, node, status, payload, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (thread_id, node, status, payload, timestamp),
            )

    def load(self, thread_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT thread_id, node, status, payload, updated_at FROM checkpoints WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "thread_id": row["thread_id"],
            "node": row["node"],
            "status": row["status"],
            "state": json.loads(row["payload"]),
            "updated_at": row["updated_at"],
        }

    def history(self, thread_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, thread_id, node, status, created_at
                FROM checkpoint_history
                WHERE thread_id = ?
                ORDER BY id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, thread_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            self._conn.execute("DELETE FROM checkpoint_history WHERE thread_id = ?", (thread_id,))

    def close(self) -> None:
        with self._lock:
            self._conn.commit()
            self._conn.close()
