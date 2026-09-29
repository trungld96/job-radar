from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from core.config import AppConfig
from core.models import Job


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self, config: AppConfig, client: httpx.Client):
        self.config = config
        self.client = client
        self.log = logging.getLogger(f"scraper.{self.name}")

    @abstractmethod
    def fetch(self) -> list[Job]:
        ...

    def _get(self, url: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", DEFAULT_UA)
        headers.setdefault("Accept", "*/*")
        return self.client.get(url, headers=headers, timeout=25.0, **kwargs)


def utc_from_epoch(seconds: float | int | None) -> datetime | None:
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(float(seconds), tz=timezone.utc)
    except (ValueError, OSError):
        return None
