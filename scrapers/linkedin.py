from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.parse import quote_plus, urlencode

from bs4 import BeautifulSoup

from .base import BaseScraper
from core.models import Job


# LinkedIn guest endpoint — HTML cards, no auth required.
# f_TPR=r604800 => posted in last 7 days (604800s).
GUEST_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?{params}"
)

# Default locations to query. Vietnam + remote worldwide for VN-friendly remote.
LOCATIONS = ["Vietnam", "Worldwide"]

# LinkedIn rate-limits aggressively (~20-30 req then 429). Keep query set small
# and sleep between requests.
JS_STACK_QUERIES = [
    "nodejs", "nestjs", "next.js", "reactjs", "typescript", "fullstack",
    "telegram mini app", "web3 developer",
]
THROTTLE_SECONDS = 1.2


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        for q in JS_STACK_QUERIES:
            for loc in LOCATIONS:
                params = urlencode({
                    "keywords": q,
                    "location": loc,
                    "f_TPR": "r604800",  # last 7 days
                    "start": 0,
                })
                try:
                    r = self._get(
                        GUEST_URL.format(params=params),
                        headers={
                            "Accept": "text/html,application/xhtml+xml",
                            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
                        },
                    )
                    r.raise_for_status()
                except Exception as exc:
                    self.log.warning("LinkedIn '%s' @ %s failed: %s", q, loc, exc)
                    time.sleep(THROTTLE_SECONDS * 2)  # back off on error
                    continue

                for job in self._parse(r.text, q, loc):
                    if job.external_id in seen:
                        continue
                    seen.add(job.external_id)
                    jobs.append(job)

                time.sleep(THROTTLE_SECONDS)
        return jobs

    def _parse(self, html: str, query: str, location: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[Job] = []
        for li in soup.find_all("li"):
            card = li.find("div", class_=re.compile(r"base-card"))
            if not card:
                continue

            # Prefer canonical link if present
            link_el = card.find("a", class_=re.compile(r"base-card__full-link"))
            url = link_el.get("href", "").split("?", 1)[0] if link_el else ""
            if not url:
                continue

            # Extract job id from URL (…-<id> at end of path)
            m = re.search(r"-(\d{6,})(?:/|$)", url)
            jid = m.group(1) if m else url

            title_el = card.find("h3", class_=re.compile(r"base-search-card__title"))
            company_el = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
            loc_el = card.find("span", class_=re.compile(r"job-search-card__location"))
            time_el = card.find("time")

            title = _text(title_el)
            company = _text(company_el)
            loc_text = _text(loc_el)

            posted_at = None
            if time_el and time_el.get("datetime"):
                try:
                    posted_at = datetime.fromisoformat(time_el["datetime"])
                except ValueError:
                    posted_at = None

            # Don't leak the search query into haystack — causes false keyword
            # matches (e.g. query "telegram mini app" matching every result).
            description = " | ".join(x for x in [company, loc_text] if x)

            out.append(
                Job(
                    source=self.name,
                    external_id=jid,
                    title=f"{title} @ {company}".strip(" @"),
                    description=description,
                    url=url,
                    posted_at=posted_at,
                    location=loc_text or None,
                    tags=[f"q:{query}", f"loc:{location}"],
                )
            )
        return out


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""
