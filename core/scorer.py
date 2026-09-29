from __future__ import annotations

from .config import AppConfig
from .matching import matches
from .models import Job


# Cap the number of matches a single group can contribute to a job's score.
# Prevents keyword-heavy job descriptions from ballooning score just because
# they mention every buzzword.
PER_GROUP_HIT_CAP = 3


def score_job(job: Job, config: AppConfig) -> None:
    """Populate job.score, job.matched_keywords, job.matched_groups in place."""
    text = job.haystack
    total = 0
    all_matched: list[str] = []
    groups: set[str] = set()

    for group_name, group in config.scoring.items():
        group_hits = 0
        for kw in group.keywords:
            if matches(text, kw):
                all_matched.append(kw)
                group_hits += 1
        if group_hits > 0:
            groups.add(group_name)
            total += min(group_hits, PER_GROUP_HIT_CAP) * group.weight

    total += config.source_boost.get(job.source, 0)

    job.score = total
    job.matched_keywords = all_matched
    job.matched_groups = sorted(groups)
