from __future__ import annotations

import re
from datetime import datetime, timezone

from .config import TrendsConfig
from .models import Trend


def _age_hours(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def apply_it_filter(trend: Trend, config: TrendsConfig) -> bool:
    """Return True if the trend matches at least one IT keyword.

    Also populates trend.matched_keywords. Uses word-boundary matching for
    short tokens (<=4 chars) to avoid "ai" matching "chair"; longer tokens
    use substring match.
    """
    hay = trend.haystack
    matched: list[str] = []
    for kw in config.it_keywords:
        if not kw:
            continue
        if len(kw) <= 4 and re.search(r"\b" + re.escape(kw) + r"\b", hay):
            matched.append(kw)
        elif len(kw) > 4 and kw in hay:
            matched.append(kw)
    trend.matched_keywords = matched
    if not config.require_it_match:
        return True
    return bool(matched)


def within_age_window(trend: Trend, config: TrendsConfig) -> bool:
    age = _age_hours(trend.posted_at)
    if age is None:
        return True  # unknown age -> let it through
    return age <= config.max_age_hours
