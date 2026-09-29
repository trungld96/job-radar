from __future__ import annotations

import logging
from typing import Iterable

import httpx

from core.models import Job


SOURCE_EMOJI = {
    "hackernews": "🟠",
    "remoteok": "🌐",
    "remotive": "💻",
    "weworkremotely": "🏠",
    "reddit": "👽",
    "upwork": "🟢",
    "freelancer": "🔵",
    "peopleperhour": "⏱️",
    "guru": "🧙",
}

MAX_MSG_LEN = 3800  # Telegram limit is 4096; leave room for markdown chars


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.log = logging.getLogger("notifier.telegram")
        self.client = httpx.Client(timeout=20.0)

    def send_job(self, job: Job) -> bool:
        text = self._format(job)
        if len(text) > MAX_MSG_LEN:
            text = text[: MAX_MSG_LEN - 3] + "..."
        return self._send(text)

    def _format(self, job: Job) -> str:
        emoji = SOURCE_EMOJI.get(job.source, "📌")
        posted = job.posted_at.strftime("%Y-%m-%d %H:%M UTC") if job.posted_at else "n/a"
        matched = ", ".join(sorted(set(job.matched_keywords))[:8]) or "-"

        desc = job.description.strip()
        if len(desc) > 900:
            desc = desc[:900] + "..."

        lines = [
            f"{emoji} *[{job.score}]* `{job.source}` — {_escape(job.title)}",
            f"🕒 {posted}",
        ]
        if job.budget_text:
            lines.append(f"💰 {_escape(job.budget_text)}")
        if job.location:
            lines.append(f"📍 {_escape(job.location)}")
        if job.tags:
            lines.append("🏷 " + ", ".join(_escape(t) for t in job.tags[:6]))
        lines.append(f"🎯 matched: {_escape(matched)}")
        lines.append("")
        lines.append(_escape(desc))
        lines.append("")
        lines.append(f"🔗 {job.url}")
        return "\n".join(lines)

    def _send(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            r = self.client.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code != 200:
                self.log.error("Telegram %s: %s", r.status_code, r.text[:200])
                return False
            return True
        except Exception as exc:
            self.log.error("Telegram send failed: %s", exc)
            return False

    def send_many(self, jobs: Iterable[Job]) -> int:
        ok = 0
        for job in jobs:
            if self.send_job(job):
                ok += 1
        return ok

    def close(self) -> None:
        self.client.close()


_MD_ESCAPE = str.maketrans({"_": r"\_", "*": r"\*", "`": r"\`", "[": r"\[", "]": r"\]"})


def _escape(text: str) -> str:
    return (text or "").translate(_MD_ESCAPE)
