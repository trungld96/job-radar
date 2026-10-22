from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from trends import ALL_SOURCES
from trends.config import load_trends_config
from trends.dedup import SeenTrendsStore
from trends.filter import apply_it_filter, within_age_window
from trends.models import Trend
from trends.notifier import TrendsNotifier


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )
    if level != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _collect(config) -> list[Trend]:
    all_trends: list[Trend] = []
    with httpx.Client(follow_redirects=True) as client:
        for name, enabled in config.sources.items():
            if not enabled:
                continue
            cls = ALL_SOURCES.get(name)
            if cls is None:
                logging.warning("Unknown trends source in config: %s", name)
                continue
            source = cls(config, client)
            try:
                items = source.fetch()
                logging.info("%s: fetched %d items", name, len(items))
                all_trends.extend(items)
            except Exception as exc:
                logging.exception("%s failed: %s", name, exc)
    return all_trends


def run(dry_run: bool = False, top: int = 0) -> int:
    root = Path(__file__).resolve().parent
    config = load_trends_config(root)
    _setup_logging(config.log_level)

    if not dry_run and (not config.telegram_token or not config.telegram_chat_id):
        logging.error(
            "Telegram not configured. Set TELEGRAM_TRENDS_CHAT_ID (and optionally "
            "TELEGRAM_TRENDS_BOT_TOKEN) in .env, or fall back to TELEGRAM_BOT_TOKEN "
            "+ TELEGRAM_CHAT_ID."
        )
        return 2

    store = SeenTrendsStore(root / "trends.db")
    notifier = (
        None if dry_run else TrendsNotifier(config.telegram_token, config.telegram_chat_id)
    )

    try:
        trends = _collect(config)
        logging.info("Collected %d raw trends across sources", len(trends))

        candidates: list[Trend] = []
        dropped = {"too_old": 0, "not_it": 0, "seen": 0}

        for t in trends:
            if not within_age_window(t, config):
                dropped["too_old"] += 1
                continue
            if not apply_it_filter(t, config):
                dropped["not_it"] += 1
                continue
            if not dry_run and store.has(t.dedup_key):
                dropped["seen"] += 1
                continue
            candidates.append(t)

        # Prefer newest first (unknown dates sink to the bottom).
        candidates.sort(
            key=lambda x: x.posted_at.timestamp() if x.posted_at else 0,
            reverse=True,
        )
        logging.info("Kept %d, dropped: %s", len(candidates), dropped)

        if dry_run:
            preview = candidates[: top or 20]
            print(f"\n=== DRY RUN — top {len(preview)} trends (not sent) ===\n")
            for t in preview:
                sig = f" [{t.score_signal}]" if t.score_signal else ""
                print(f"{t.source:<16}{sig} {t.title[:90]}")
                if t.matched_keywords:
                    print(f"    matched: {', '.join(t.matched_keywords[:6])}")
                print(f"    {t.url}")
                print()
            return 0

        assert notifier is not None
        sent = 0
        for t in candidates:
            if notifier.send(t):
                store.mark(
                    dedup_key=t.dedup_key, source=t.source, title=t.title, url=t.url
                )
                sent += 1
        logging.info("Sent %d trend alerts to Telegram", sent)
        return 0
    finally:
        if notifier is not None:
            notifier.close()
        store.close()


def _cli() -> int:
    p = argparse.ArgumentParser(description="IT Trend Radar")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch + filter but do NOT send to Telegram; print preview.")
    p.add_argument("--top", type=int, default=20,
                   help="Number of items to preview in --dry-run (default 20).")
    args = p.parse_args()
    return run(dry_run=args.dry_run, top=args.top)


if __name__ == "__main__":
    sys.exit(_cli())
