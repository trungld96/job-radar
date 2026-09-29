from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime

import feedparser

from .base import BaseScraper
from core.models import Job


FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]


class WeWorkRemotelyScraper(BaseScraper):
    name = "weworkremotely"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for feed_url in FEEDS:
            try:
                r = self._get(feed_url)
                r.raise_for_status()
                parsed = feedparser.parse(r.content)
            except Exception as exc:
                self.log.warning("WWR feed failed: %s (%s)", feed_url, exc)
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
                        external_id=link.rsplit("/", 1)[-1] or link,
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
