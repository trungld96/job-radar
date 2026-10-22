from __future__ import annotations

import html
import re
from datetime import datetime
from time import mktime

import feedparser

from .base import BaseScraper
from core.models import Job


# vLance publishes a global "latest projects" feed. No per-keyword filter —
# scoring layer handles that against our stack keywords.
FEED_URL = "https://www.vlance.vn/rss.xml"


class VlanceScraper(BaseScraper):
    name = "vlance"

    def fetch(self) -> list[Job]:
        try:
            r = self._get(
                FEED_URL,
                headers={
                    "Accept": "application/rss+xml, application/xml;q=0.9",
                    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
                },
            )
            r.raise_for_status()
        except Exception as exc:
            self.log.warning("vLance RSS failed: %s", exc)
            return []

        parsed = feedparser.parse(r.content)
        jobs: list[Job] = []
        for entry in parsed.entries:
            link = entry.get("link", "")
            if not link:
                continue

            posted_at = None
            if entry.get("published_parsed"):
                try:
                    posted_at = datetime.fromtimestamp(mktime(entry.published_parsed))
                except (OverflowError, ValueError):
                    posted_at = None

            desc = _clean(entry.get("summary", "") or entry.get("description", ""))
            budget = _extract_budget(desc)

            # Vlance slug carries no numeric id — use the slug itself for dedup.
            slug = link.rstrip("/").rsplit("/", 1)[-1]

            jobs.append(
                Job(
                    source=self.name,
                    external_id=slug or link,
                    title=entry.get("title", ""),
                    description=desc,
                    url=link,
                    posted_at=posted_at,
                    budget_text=budget,
                )
            )
        return jobs


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


BUDGET_RE = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d{2,})\s*(?:-\s*(\d{1,3}(?:[.,]\d{3})+|\d{2,}))?\s*(VND|đ|USD|\$)",
    re.IGNORECASE,
)


def _extract_budget(text: str) -> str | None:
    m = BUDGET_RE.search(text)
    if not m:
        return None
    lo, hi, cur = m.group(1), m.group(2), m.group(3)
    return f"{lo}-{hi} {cur}" if hi else f"{lo} {cur}"
