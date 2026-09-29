from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseScraper
from core.models import Job


API_URL = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def fetch(self) -> list[Job]:
        r = self._get(API_URL, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []

        jobs: list[Job] = []
        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue
            desc = item.get("description") or ""
            title = item.get("position") or item.get("title") or ""
            company = item.get("company") or ""
            posted_at = None
            date_raw = item.get("date")
            if date_raw:
                try:
                    posted_at = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(item["id"]),
                    title=f"{title} @ {company}".strip(" @"),
                    description=_clean(desc),
                    url=item.get("url") or item.get("apply_url") or "",
                    posted_at=posted_at,
                    tags=[t for t in (item.get("tags") or []) if isinstance(t, str)],
                    location=item.get("location") or None,
                )
            )
        return jobs


def _clean(text: str) -> str:
    import html
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
