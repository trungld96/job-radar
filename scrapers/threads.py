from __future__ import annotations

import codecs
import re
from urllib.parse import quote_plus

from .base import BaseScraper, utc_from_epoch
from core.models import Job


# Threads has no official public API. The search page renders results server-side
# only when logged in; without auth, hashtag pages are the most reliable
# unauthenticated surface. Fall back to search endpoint anyway.
HASHTAG_URL = "https://www.threads.net/tag/{tag}"
SEARCH_URL = "https://www.threads.net/search?q={q}&serp_type=default"

# Regex over embedded JSON — Threads server embeds post data as inline <script>.
# Extracts "code" (shortcode used in URLs) + "caption":{"text":"..."}.
POST_RE = re.compile(
    r'"code"\s*:\s*"([A-Za-z0-9_\-]{8,20})"[^{]{0,400}?"caption"\s*:\s*\{[^}]{0,20}"text"\s*:\s*"((?:[^"\\]|\\.){40,2000})"',
    re.DOTALL,
)
USER_RE = re.compile(r'"username"\s*:\s*"([A-Za-z0-9._]+)"')
TAKEN_AT_RE = re.compile(r'"taken_at"\s*:\s*(\d{9,13})')


class ThreadsScraper(BaseScraper):
    """Keyword scan on Threads via hashtag + search pages.

    Unofficial — Meta can change embedded JSON shape anytime. Keep disabled by
    default; enable in config.yaml when you want to try it.
    """

    name = "threads"

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }

        urls: list[tuple[str, str]] = []
        for q in self.config.search_queries:
            tag = re.sub(r"[^a-z0-9]+", "", q.lower())
            if tag:
                urls.append((f"tag:{tag}", HASHTAG_URL.format(tag=tag)))
            urls.append((f"search:{q}", SEARCH_URL.format(q=quote_plus(q))))

        for label, url in urls:
            try:
                r = self._get(url, headers=headers)
                r.raise_for_status()
            except Exception as exc:
                self.log.warning("Threads %s failed: %s", label, exc)
                continue

            for post in self._extract_posts(r.text):
                code = post["code"]
                if code in seen:
                    continue
                seen.add(code)

                caption = post["caption"]
                username = post.get("username") or ""
                post_url = (
                    f"https://www.threads.net/@{username}/post/{code}"
                    if username
                    else f"https://www.threads.net/t/{code}"
                )

                jobs.append(
                    Job(
                        source=self.name,
                        external_id=code,
                        title=caption[:120].split("\n", 1)[0].strip() or caption[:120],
                        description=caption,
                        url=post_url,
                        posted_at=utc_from_epoch(post.get("taken_at")),
                        tags=[label],
                    )
                )
        return jobs

    def _extract_posts(self, html: str) -> list[dict]:
        posts: list[dict] = []

        # Build a per-post context slice so we can co-locate username/taken_at.
        for m in POST_RE.finditer(html):
            code = m.group(1)
            caption = _unescape(m.group(2))

            start = max(0, m.start() - 400)
            end = min(len(html), m.end() + 400)
            window = html[start:end]
            user_m = USER_RE.search(window)
            taken_m = TAKEN_AT_RE.search(window)

            posts.append(
                {
                    "code": code,
                    "caption": caption,
                    "username": user_m.group(1) if user_m else None,
                    "taken_at": int(taken_m.group(1)) if taken_m else None,
                }
            )
        return posts


def _unescape(s: str) -> str:
    # Threads embeds unicode as \uXXXX plus \n/\t etc. Keep failures silent.
    try:
        return codecs.decode(s, "unicode_escape")
    except Exception:
        return s
