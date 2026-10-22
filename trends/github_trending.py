from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import BaseTrendSource
from .models import Trend


BASE = "https://github.com/trending"


class GitHubTrendingSource(BaseTrendSource):
    """Scrape github.com/trending (daily) for one or more languages."""

    name = "github_trending"

    def fetch(self) -> list[Trend]:
        trends: list[Trend] = []
        seen: set[str] = set()

        for lang in self.config.github_languages or [""]:
            url = BASE if not lang else f"{BASE}/{lang}"
            url = f"{url}?since=daily"
            lang_label = lang or "overall"
            try:
                r = self._get(url, headers={"Accept": "text/html"})
                r.raise_for_status()
            except Exception as exc:
                self.log.warning("GitHub Trending fetch failed: %s (%s)", url, exc)
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.select("article.Box-row")
            for rank, art in enumerate(articles[: self.config.max_items_per_source], start=1):
                h2 = art.select_one("h2 a")
                if not h2:
                    continue
                href = (h2.get("href") or "").strip()
                if not href or href in seen:
                    continue
                seen.add(href)

                owner_repo = href.strip("/")
                repo_url = f"https://github.com{href}"

                desc_tag = art.select_one("p")
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                lang_tag = art.select_one("[itemprop='programmingLanguage']")
                repo_lang = lang_tag.get_text(strip=True) if lang_tag else ""

                stars_today_tag = art.select_one("span.d-inline-block.float-sm-right")
                stars_today = (
                    _digits(stars_today_tag.get_text(strip=True))
                    if stars_today_tag
                    else ""
                )

                total_stars = ""
                forks = ""
                for a in art.select("a.Link--muted"):
                    href_mu = (a.get("href") or "")
                    if "/stargazers" in href_mu:
                        total_stars = _digits(a.get_text(strip=True))
                    elif "/forks" in href_mu or "/network/members" in href_mu:
                        forks = _digits(a.get_text(strip=True))

                sig_parts = []
                if stars_today:
                    sig_parts.append(f"⭐ +{stars_today} today")
                if total_stars:
                    sig_parts.append(f"★ {total_stars} total")
                if repo_lang:
                    sig_parts.append(repo_lang)

                why_bits = [f"GitHub Trending #{rank} ({lang_label}) today"]
                if stars_today:
                    why_bits.append(f"+{stars_today} stars in 24h")
                if total_stars:
                    why_bits.append(f"{total_stars} total ★")
                if forks:
                    why_bits.append(f"{forks} forks")
                why_hot = " · ".join(why_bits)

                tags = [repo_lang.lower()] if repo_lang else []

                trends.append(
                    Trend(
                        source=self.name,
                        external_id=owner_repo,
                        title=owner_repo,
                        description=description,
                        url=repo_url,
                        score_signal=" · ".join(sig_parts) or None,
                        why_hot=why_hot,
                        tags=tags,
                    )
                )
        return trends


def _digits(text: str) -> str:
    m = re.search(r"[\d,]+", text or "")
    return m.group(0) if m else ""
