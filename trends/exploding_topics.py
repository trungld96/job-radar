from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime

import feedparser

from .base import BaseTrendSource
from .models import Trend


# Exploding Topics does not expose a free trending-topics API. Their blog
# RSS surfaces recent trend writeups which are a reasonable proxy; the
# source degrades gracefully if the feed is unreachable or restructured.
CANDIDATE_FEEDS = [
    "https://explodingtopics.com/blog/feed",
    "https://explodingtopics.com/blog/rss",
    "https://explodingtopics.com/feed",
]


class ExplodingTopicsSource(BaseTrendSource):
    name = "exploding_topics"

    def fetch(self) -> list[Trend]:
        trends: list[Trend] = []
        seen: set[str] = set()

        for feed_url in CANDIDATE_FEEDS:
            try:
                r = self._get(feed_url)
                if r.status_code != 200:
                    continue
                parsed = feedparser.parse(r.content)
                if not parsed.entries:
                    continue
            except Exception as exc:
                self.log.warning("Exploding Topics feed failed: %s (%s)", feed_url, exc)
                continue

            for entry in parsed.entries[: self.config.max_items_per_source]:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)

                posted_at = None
                if entry.get("published_parsed"):
                    posted_at = datetime.fromtimestamp(mktime(entry.published_parsed))

                trends.append(
                    Trend(
                        source=self.name,
                        external_id=link,
                        title=entry.get("title", "").strip(),
                        description=_clean(entry.get("summary", "")),
                        url=link,
                        posted_at=posted_at,
                    )
                )
            if trends:
                break  # first working feed wins

        if not trends:
            self.log.info("Exploding Topics: no accessible feed, skipping.")
        return trends


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
