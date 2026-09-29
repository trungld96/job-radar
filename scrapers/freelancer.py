from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

from .base import BaseScraper
from core.models import Job


API_URL = (
    "https://www.freelancer.com/api/projects/0.1/projects/active/"
    "?query={q}&limit=30&full_description=true&job_details=true&user_details=true"
    "&project_types[]=fixed&project_types[]=hourly&compact=true"
)


class FreelancerScraper(BaseScraper):
    name = "freelancer"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for q in self.config.search_queries:
            try:
                r = self._get(
                    API_URL.format(q=quote_plus(q)),
                    headers={"Accept": "application/json"},
                )
                r.raise_for_status()
                payload = r.json()
            except Exception as exc:
                self.log.warning("Freelancer query '%s' failed: %s", q, exc)
                continue

            projects = ((payload.get("result") or {}).get("projects")) or []
            for p in projects:
                pid = str(p.get("id"))
                if pid in seen:
                    continue
                seen.add(pid)

                seo = p.get("seo_url") or ""
                url = f"https://www.freelancer.com/projects/{seo}" if seo else \
                      f"https://www.freelancer.com/projects/{pid}"

                budget = p.get("budget") or {}
                budget_text = None
                if budget:
                    cur = (p.get("currency") or {}).get("code", "USD")
                    lo, hi = budget.get("minimum"), budget.get("maximum")
                    if lo and hi:
                        budget_text = f"{cur} {lo}-{hi}"
                    elif lo:
                        budget_text = f"{cur} {lo}+"

                submitted = p.get("submitdate")
                posted_at = (
                    datetime.fromtimestamp(submitted, tz=timezone.utc) if submitted else None
                )

                jobs.append(
                    Job(
                        source=self.name,
                        external_id=pid,
                        title=p.get("title", ""),
                        description=p.get("preview_description") or p.get("description") or "",
                        url=url,
                        posted_at=posted_at,
                        budget_text=budget_text,
                        tags=[j.get("name", "") for j in (p.get("jobs") or []) if j.get("name")],
                    )
                )
        return jobs
