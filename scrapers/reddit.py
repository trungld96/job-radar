from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseScraper
from core.models import Job


LISTING = "https://www.reddit.com/r/{sub}/new.json?limit=50"


class RedditScraper(BaseScraper):
    name = "reddit"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        for sub in self.config.reddit_subs:
            try:
                r = self._get(
                    LISTING.format(sub=sub),
                    headers={"Accept": "application/json"},
                )
                r.raise_for_status()
            except Exception as exc:
                self.log.warning("Reddit /r/%s failed: %s", sub, exc)
                continue

            data = r.json().get("data", {}).get("children", [])
            for child in data:
                post = child.get("data", {})
                title = post.get("title", "") or ""

                # r/forhire uses [HIRING] / [FOR HIRE] tags — we only want HIRING posts.
                lowered = title.lower()
                if sub.lower() == "forhire" and "[hiring]" not in lowered:
                    continue

                created = post.get("created_utc")
                posted_at = (
                    datetime.fromtimestamp(created, tz=timezone.utc) if created else None
                )
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=str(post.get("id")),
                        title=title,
                        description=post.get("selftext", "") or "",
                        url="https://www.reddit.com" + (post.get("permalink") or ""),
                        posted_at=posted_at,
                        tags=[f"r/{sub}"],
                    )
                )
        return jobs
