from __future__ import annotations

import html
import re
from datetime import datetime

from .base import BaseScraper
from core.models import Job


API_URL = "https://remotive.com/api/remote-jobs?category=software-dev"


class RemotiveScraper(BaseScraper):
    name = "remotive"

    def fetch(self) -> list[Job]:
        r = self._get(API_URL, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        items = data.get("jobs", []) if isinstance(data, dict) else []

        jobs: list[Job] = []
        for item in items:
            posted_at = None
            date_raw = item.get("publication_date")
            if date_raw:
                try:
                    posted_at = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            desc = _clean(item.get("description") or "")
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=f"{item.get('title', '')} @ {item.get('company_name', '')}".strip(" @"),
                    description=desc,
                    url=item.get("url") or "",
                    posted_at=posted_at,
                    tags=[t for t in (item.get("tags") or []) if isinstance(t, str)],
                    location=item.get("candidate_required_location") or None,
                    budget_text=item.get("salary") or None,
                )
            )
        return jobs


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
