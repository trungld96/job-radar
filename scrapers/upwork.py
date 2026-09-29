from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime
from urllib.parse import quote_plus

import feedparser

from .base import BaseScraper
from core.models import Job


FEED_TEMPLATE = "https://www.upwork.com/ab/feed/jobs/rss?q={q}&sort=recency&paging=0%3B50"


class UpworkScraper(BaseScraper):
    """Upwork's public RSS is intermittently rate-limited/gated.
    We treat any failure as a warning and move on."""

    name = "upwork"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for q in self.config.search_queries:
            url = FEED_TEMPLATE.format(q=quote_plus(q))
            try:
                r = self._get(url)
                r.raise_for_status()
                parsed = feedparser.parse(r.content)
            except Exception as exc:
                self.log.warning("Upwork query '%s' failed: %s", q, exc)
                continue

            if not parsed.entries:
                continue

            for entry in parsed.entries:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)

                posted_at = None
                if entry.get("published_parsed"):
                    posted_at = datetime.fromtimestamp(mktime(entry.published_parsed))

                jobs.append(
                    Job(
                        source=self.name,
                        external_id=link,
                        title=entry.get("title", ""),
                        description=_clean(entry.get("summary", "")),
                        url=link,
                        posted_at=posted_at,
                        tags=[f"query:{q}"],
                    )
                )
        return jobs


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
