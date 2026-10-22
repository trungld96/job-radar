from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Trend:
    source: str
    external_id: str
    title: str
    description: str
    url: str
    posted_at: Optional[datetime] = None
    score_signal: Optional[str] = None
    why_hot: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    author: Optional[str] = None
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> str:
        raw = f"{self.source}::{self.external_id}".encode("utf-8", "ignore")
        return hashlib.sha1(raw).hexdigest()

    @property
    def haystack(self) -> str:
        return (
            f"{self.title}\n{self.description}\n{' '.join(self.tags)}"
        ).lower()
