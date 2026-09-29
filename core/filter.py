from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import AppConfig
from .matching import matches
from .models import Job


def is_blacklisted(job: Job, blacklist: list[str]) -> str | None:
    text = job.haystack
    for phrase in blacklist:
        if matches(text, phrase):
            return phrase
    return None


def is_too_old(job: Job, max_age_hours: int) -> bool:
    if job.posted_at is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    posted = job.posted_at
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    return posted < cutoff


def should_keep(job: Job, config: AppConfig) -> tuple[bool, str]:
    """Return (keep?, reason). reason only meaningful when keep is False.
    Note: this runs BEFORE scoring; stack-gate check runs after in main."""
    reason = is_blacklisted(job, config.blacklist)
    if reason:
        return False, f"blacklist:{reason}"
    if is_too_old(job, config.max_age_hours):
        return False, "too_old"
    return True, ""


def passes_stack_gate(job: Job, config: AppConfig) -> bool:
    """After scoring, verify job matched at least one primary/specialty keyword."""
    if not config.require_stack_match:
        return True
    return any(g in job.matched_groups for g in config.stack_gate_groups)
