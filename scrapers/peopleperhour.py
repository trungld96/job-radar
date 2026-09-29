from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime

import feedparser

from .base import BaseScraper
from core.models import Job


FEEDS = [
    "https://www.peopleperhour.com/services/technology-programming.rss",
    "https://www.peopleperhour.com/freelance-jobs?ref=feed",
]


class PeoplePerHourScraper(BaseScraper):
    name = "peopleperhour"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for feed_url in FEEDS:
            try:
                r = self._get(feed_url)
                r.raise_for_status()
                parsed = feedparser.parse(r.content)
            except Exception as exc:
                self.log.warning("PPH feed failed: %s (%s)", feed_url, exc)
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
                    )
                )
        return jobs


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
