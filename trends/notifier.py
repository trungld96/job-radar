from __future__ import annotations

import logging

import httpx

from .models import Trend


SOURCE_EMOJI = {
    "producthunt": "🚀",
    "hackernews": "🟠",
    "github_trending": "🐙",
    "exploding_topics": "📈",
}

MAX_MSG_LEN = 3800


class TrendsNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.log = logging.getLogger("trends.notifier")
        self.client = httpx.Client(timeout=20.0)

    def send(self, trend: Trend) -> bool:
        text = self._format(trend)
        if len(text) > MAX_MSG_LEN:
            text = text[: MAX_MSG_LEN - 3] + "..."
        return self._send(text)

    def _format(self, trend: Trend) -> str:
        emoji = SOURCE_EMOJI.get(trend.source, "📌")
        posted = (
            trend.posted_at.strftime("%Y-%m-%d %H:%M UTC") if trend.posted_at else "n/a"
        )
        desc = (trend.description or "").strip()
        if len(desc) > 700:
            desc = desc[:700] + "..."

        lines = [f"{emoji} `{trend.source}` — *{_escape(trend.title)}*"]
        if trend.why_hot:
            lines.append(f"🔥 *Why hot:* {_escape(trend.why_hot)}")
        elif trend.score_signal:
            lines.append(f"📊 {_escape(trend.score_signal)}")
        if trend.author:
            lines.append(f"👤 {_escape(trend.author)}")
        lines.append(f"🕒 {posted}")
        if trend.matched_keywords:
            matched = ", ".join(sorted(set(trend.matched_keywords))[:8])
            lines.append(f"🎯 topics: {_escape(matched)}")
        if desc:
            lines.append("")
            lines.append(_escape(desc))
        lines.append("")
        lines.append(f"🔗 {trend.url}")
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

    def close(self) -> None:
        self.client.close()


_MD_ESCAPE = str.maketrans({"_": r"\_", "*": r"\*", "`": r"\`", "[": r"\[", "]": r"\]"})


def _escape(text: str) -> str:
    return (text or "").translate(_MD_ESCAPE)
