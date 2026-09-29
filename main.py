from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

# Windows cp1252 console can't handle unicode in log messages.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.config import load_config
from core.dedup import SeenStore
from core.filter import passes_stack_gate, should_keep
from core.models import Job
from core.scorer import score_job
from notifier.telegram import TelegramNotifier
from scrapers import ALL_SCRAPERS


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down httpx per-request logs unless in DEBUG.
    if level != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _collect(config) -> list[Job]:
    all_jobs: list[Job] = []
    with httpx.Client(follow_redirects=True) as client:
        for name, enabled in config.sources.items():
            if not enabled:
                continue
            cls = ALL_SCRAPERS.get(name)
            if cls is None:
                logging.warning("Unknown source in config: %s", name)
                continue

            scraper = cls(config, client)
            try:
                jobs = scraper.fetch()
                logging.info("%s: fetched %d jobs", name, len(jobs))
                all_jobs.extend(jobs)
            except Exception as exc:
                logging.exception("%s failed: %s", name, exc)
    return all_jobs


def run(dry_run: bool = False, top: int = 0) -> int:
    root = Path(__file__).resolve().parent
    config = load_config(root)
    _setup_logging(config.log_level)

    if not dry_run and (not config.telegram_token or not config.telegram_chat_id):
        logging.error(
            "Telegram not configured. Fill TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env"
        )
        return 2

    store = SeenStore(root / "storage.db")
    notifier = None if dry_run else TelegramNotifier(config.telegram_token, config.telegram_chat_id)

    try:
        jobs = _collect(config)
        logging.info("Collected %d raw jobs across sources", len(jobs))

        candidates: list[Job] = []
        dropped = {
            "blacklist": 0, "too_old": 0, "stack_gate": 0,
            "low_score": 0, "seen": 0,
        }

        for job in jobs:
            keep, reason = should_keep(job, config)
            if not keep:
                key = reason.split(":", 1)[0]
                dropped[key] = dropped.get(key, 0) + 1
                continue

            score_job(job, config)

            if not passes_stack_gate(job, config):
                dropped["stack_gate"] += 1
                continue

            if job.score < config.min_score:
                dropped["low_score"] += 1
                continue

            if not dry_run and store.has(job.dedup_key):
                dropped["seen"] += 1
                continue

            candidates.append(job)

        candidates.sort(key=lambda j: j.score, reverse=True)
        logging.info("Kept %d, dropped: %s", len(candidates), dropped)

        if dry_run:
            preview = candidates[: top or 20]
            print("\n=== DRY RUN — top", len(preview), "candidates (not sent) ===\n")
            for j in preview:
                print(f"[{j.score:>3}] {j.source:<14} {j.title[:80]}")
                print(f"      groups: {','.join(j.matched_groups)}  matched: {', '.join(j.matched_keywords[:6])}")
                if j.budget_text:
                    print(f"      budget: {j.budget_text}")
                print(f"      {j.url}")
                print()
            return 0

        assert notifier is not None
        sent = 0
        for job in candidates:
            if notifier.send_job(job):
                store.mark(
                    dedup_key=job.dedup_key,
                    source=job.source,
                    title=job.title,
                    url=job.url,
                    score=job.score,
                )
                sent += 1

        logging.info("Sent %d alerts to Telegram", sent)
        return 0
    finally:
        if notifier is not None:
            notifier.close()
        store.close()


def _cli() -> int:
    p = argparse.ArgumentParser(description="Job Radar")
    p.add_argument("--dry-run", action="store_true",
                   help="Score + rank but do NOT send to Telegram; print top matches.")
    p.add_argument("--top", type=int, default=20,
                   help="Number of candidates to preview in --dry-run mode (default 20).")
    args = p.parse_args()
    return run(dry_run=args.dry_run, top=args.top)


if __name__ == "__main__":
    sys.exit(_cli())
