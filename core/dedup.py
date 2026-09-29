from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SeenStore:
    """SQLite-backed 'have we already alerted on this job?' tracker."""

    def __init__(self, path: Path):
        self.path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                dedup_key TEXT PRIMARY KEY,
                source     TEXT NOT NULL,
                title      TEXT NOT NULL,
                url        TEXT NOT NULL,
                score      INTEGER NOT NULL,
                sent_at    TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def has(self, dedup_key: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen_jobs WHERE dedup_key = ? LIMIT 1", (dedup_key,)
        )
        return cur.fetchone() is not None

    def mark(self, *, dedup_key: str, source: str, title: str, url: str, score: int) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_jobs(dedup_key, source, title, url, score, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (dedup_key, source, title, url, score, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
