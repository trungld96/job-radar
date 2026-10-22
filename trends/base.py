from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from .config import TrendsConfig
from .models import Trend


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


class BaseTrendSource(ABC):
    name: str = "base"

    def __init__(self, config: TrendsConfig, client: httpx.Client):
        self.config = config
        self.client = client
        self.log = logging.getLogger(f"trends.{self.name}")

    @abstractmethod
    def fetch(self) -> list[Trend]:
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
