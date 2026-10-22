from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SeenTrendsStore:
    """SQLite-backed 'have we already alerted on this trend?' tracker."""

    def __init__(self, path: Path):
        self.path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_trends (
                dedup_key TEXT PRIMARY KEY,
                source    TEXT NOT NULL,
                title     TEXT NOT NULL,
                url       TEXT NOT NULL,
                sent_at   TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def has(self, dedup_key: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen_trends WHERE dedup_key = ? LIMIT 1", (dedup_key,)
        )
        return cur.fetchone() is not None

    def mark(self, *, dedup_key: str, source: str, title: str, url: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_trends(dedup_key, source, title, url, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (dedup_key, source, title, url, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
