from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime

import feedparser

from .base import BaseTrendSource
from .models import Trend


# Product Hunt publishes a public RSS of the top products of the day,
# ranked by upvotes.
FEEDS = [
    "https://www.producthunt.com/feed",
]


class ProductHuntSource(BaseTrendSource):
    name = "producthunt"

    def fetch(self) -> list[Trend]:
        trends: list[Trend] = []
        seen: set[str] = set()
        for feed_url in FEEDS:
            try:
                r = self._get(feed_url)
                r.raise_for_status()
                parsed = feedparser.parse(r.content)
            except Exception as exc:
                self.log.warning("Product Hunt feed failed: %s (%s)", feed_url, exc)
                continue

            entries = parsed.entries[: self.config.max_items_per_source]
            total = len(entries)
            for idx, entry in enumerate(entries, start=1):
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)

                posted_at = None
                if entry.get("published_parsed"):
                    posted_at = datetime.fromtimestamp(mktime(entry.published_parsed))

                title = entry.get("title", "").strip()
                summary = _clean(entry.get("summary", ""))

                why_hot = (
                    f"Top launch on Product Hunt today · ranked #{idx} of {total}"
                )

                trends.append(
                    Trend(
                        source=self.name,
                        external_id=link.rsplit("/", 1)[-1] or link,
                        title=title,
                        description=summary,
                        url=link,
                        posted_at=posted_at,
                        score_signal=f"#{idx} of {total} today",
                        why_hot=why_hot,
                    )
                )
        return trends


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
