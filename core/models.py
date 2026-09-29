from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    description: str
    url: str
    posted_at: Optional[datetime] = None
    budget_text: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    location: Optional[str] = None

    score: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    matched_groups: list[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> str:
        raw = f"{self.source}::{self.external_id}".encode("utf-8", "ignore")
        return hashlib.sha1(raw).hexdigest()

    @property
    def haystack(self) -> str:
        return f"{self.title}\n{self.description}".lower()
