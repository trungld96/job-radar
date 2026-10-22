from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class TrendsConfig:
    max_age_hours: int
    require_it_match: bool
    max_items_per_source: int
    sources: dict[str, bool]
    github_languages: list[str]
    it_keywords: list[str]

    telegram_token: str
    telegram_chat_id: str
    log_level: str

    root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)


def load_trends_config(root: Path | None = None) -> TrendsConfig:
    root = root or Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    with (root / "trends.yaml").open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    main_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    main_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    trends_token = os.getenv("TELEGRAM_TRENDS_BOT_TOKEN", "").strip() or main_token
    trends_chat = os.getenv("TELEGRAM_TRENDS_CHAT_ID", "").strip() or main_chat

    return TrendsConfig(
        max_age_hours=int(raw.get("max_age_hours", 48)),
        require_it_match=bool(raw.get("require_it_match", True)),
        max_items_per_source=int(raw.get("max_items_per_source", 30)),
        sources={k: bool(v) for k, v in (raw.get("sources") or {}).items()},
        github_languages=[str(x) for x in (raw.get("github_languages") or [""])],
        it_keywords=[str(k).lower() for k in (raw.get("it_keywords") or [])],
        telegram_token=trends_token,
        telegram_chat_id=trends_chat,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        root=root,
    )
