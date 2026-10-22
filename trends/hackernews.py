from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from .base import BaseTrendSource, utc_from_epoch
from .models import Trend


# Algolia HN search API — free, no auth.
# front_page = currently on the HN front page (voted up by the community).
# story + "Show HN" filter = Show HN launches (new indie product reveals).
FRONT_PAGE = (
    "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={n}"
)
SHOW_HN = (
    "https://hn.algolia.com/api/v1/search_by_date?query=Show+HN"
    "&tags=story&hitsPerPage={n}"
)


class HackerNewsFrontSource(BaseTrendSource):
    """Front-page HN stories + recent Show HN launches."""

    name = "hackernews"

    def fetch(self) -> list[Trend]:
        trends: list[Trend] = []
        seen: set[str] = set()

        queries = [
            (
                FRONT_PAGE.format(n=self.config.max_items_per_source),
                "front_page",
                "On HN front page",
            ),
            (
                SHOW_HN.format(n=self.config.max_items_per_source),
                "show_hn",
                "New Show HN launch",
            ),
        ]

        for url, bucket, why_prefix in queries:
            try:
                r = self._get(url)
                r.raise_for_status()
                hits = r.json().get("hits", [])
            except Exception as exc:
                self.log.warning("HN query failed: %s (%s)", url, exc)
                continue

            for hit in hits:
                obj_id = str(hit.get("objectID") or "")
                if not obj_id or obj_id in seen:
                    continue
                seen.add(obj_id)

                title = (hit.get("title") or "").strip()
                if not title:
                    continue
                external_url = (hit.get("url") or "").strip()
                hn_url = f"https://news.ycombinator.com/item?id={obj_id}"
                points = int(hit.get("points") or 0)
                num_comments = int(hit.get("num_comments") or 0)
                created = utc_from_epoch(hit.get("created_at_i"))

                desc = _clean(hit.get("story_text") or "")
                if not desc:
                    desc = f"{points} points · {num_comments} comments on Hacker News"

                tags = [t for t in (hit.get("_tags") or []) if isinstance(t, str)]
                tags.append(bucket)

                why_bits = [why_prefix, f"▲ {points}", f"💬 {num_comments}"]
                vph = _votes_per_hour(points, created)
                if vph is not None:
                    why_bits.append(f"{vph:.1f} pts/hr")
                why_hot = " · ".join(why_bits)

                trends.append(
                    Trend(
                        source=self.name,
                        external_id=obj_id,
                        title=title,
                        description=desc,
                        url=external_url or hn_url,
                        posted_at=created,
                        score_signal=f"▲ {points} · 💬 {num_comments}",
                        why_hot=why_hot,
                        author=hit.get("author"),
                        tags=tags,
                    )
                )
        return trends


def _votes_per_hour(points: int, created: datetime | None) -> float | None:
    if not created or points <= 0:
        return None
    age_hr = (datetime.now(timezone.utc) - created).total_seconds() / 3600.0
    if age_hr < 0.25:
        return None
    return points / age_hr


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()
