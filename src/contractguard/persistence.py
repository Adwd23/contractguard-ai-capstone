"""Durable LangGraph SQLite checkpoint persistence.

This module intentionally uses LangGraph's SqliteSaver as the checkpointer that the
compiled StateGraph receives. It therefore persists the exact graph execution state,
including interrupt position, rather than mirroring state in a custom table.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver


class LangGraphSQLitePersistence:
    """Own the SQLite connection and the real LangGraph SqliteSaver instance."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = RLock()
        os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self.saver = SqliteSaver(self._conn)
        self.saver.setup()

    @staticmethod
    def config(thread_id: str, *, recursion_limit: int | None = None) -> dict[str, Any]:
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        if recursion_limit is not None:
            config["recursion_limit"] = recursion_limit
        return config

    def thread_exists(self, thread_id: str) -> bool:
        with self._lock:
            return self.saver.get_tuple(self.config(thread_id)) is not None

    def close(self) -> None:
        with self._lock:
            self._conn.commit()
            self._conn.close()
