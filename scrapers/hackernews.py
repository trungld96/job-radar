from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from .base import BaseScraper, utc_from_epoch
from core.models import Job


# Algolia HN search API — free, no auth.
SEARCH_STORY = "https://hn.algolia.com/api/v1/search?query={q}&tags=story&hitsPerPage=5"
SEARCH_COMMENTS = "https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_{sid}&hitsPerPage=200"


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


class HackerNewsScraper(BaseScraper):
    """Scrapes the latest 'Ask HN: Who is hiring?' thread — each top comment is a job."""

    name = "hackernews"

    def fetch(self) -> list[Job]:
        story_id = self._latest_hiring_story_id()
        if not story_id:
            self.log.warning("No 'Who is hiring' story found")
            return []

        r = self._get(SEARCH_COMMENTS.format(sid=story_id))
        r.raise_for_status()
        hits = r.json().get("hits", [])

        jobs: list[Job] = []
        for hit in hits:
            text = _strip_html(hit.get("comment_text", ""))
            if len(text) < 80:
                continue
            title = text[:120].split("\n", 1)[0].strip()
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(hit["objectID"]),
                    title=title,
                    description=text,
                    url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    posted_at=utc_from_epoch(hit.get("created_at_i")),
                )
            )
        return jobs

    def _latest_hiring_story_id(self) -> str | None:
        r = self._get(SEARCH_STORY.format(q="Ask+HN%3A+Who+is+hiring"))
        r.raise_for_status()
        hits = r.json().get("hits", [])
        for hit in hits:
            title = (hit.get("title") or "").lower()
            if "who is hiring" in title and hit.get("author", "").lower() == "whoishiring":
                return str(hit["objectID"])
        return str(hits[0]["objectID"]) if hits else None
