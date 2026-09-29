from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class ScoringGroup:
    weight: int
    keywords: list[str]


@dataclass
class AppConfig:
    min_score: int
    max_age_hours: int
    require_stack_match: bool
    sources: dict[str, bool]
    source_boost: dict[str, int]
    reddit_subs: list[str]
    search_queries: list[str]
    scoring: dict[str, ScoringGroup]
    blacklist: list[str]

    telegram_token: str
    telegram_chat_id: str
    log_level: str

    # Groups that satisfy the stack-match gate.
    stack_gate_groups: tuple[str, ...] = ("primary_stack", "portfolio_specialty")

    root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)


def load_config(root: Path | None = None) -> AppConfig:
    root = root or Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    with (root / "config.yaml").open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    scoring_raw = raw.get("scoring", {})
    scoring: dict[str, ScoringGroup] = {}
    blacklist: list[str] = []
    for name, group in scoring_raw.items():
        if name == "blacklist":
            blacklist = [k.lower() for k in group]
            continue
        scoring[name] = ScoringGroup(
            weight=int(group["weight"]),
            keywords=[k.lower() for k in group["keywords"]],
        )

    return AppConfig(
        min_score=int(raw.get("min_score", 40)),
        max_age_hours=int(raw.get("max_age_hours", 72)),
        require_stack_match=bool(raw.get("require_stack_match", True)),
        sources={k: bool(v) for k, v in raw.get("sources", {}).items()},
        source_boost={k: int(v) for k, v in (raw.get("source_boost") or {}).items()},
        reddit_subs=list(raw.get("reddit_subs", [])),
        search_queries=list(raw.get("search_queries", [])),
        scoring=scoring,
        blacklist=blacklist,
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        root=root,
    )
