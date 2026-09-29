"""
One-time helper: fetches the chat_id of the last message sent TO your bot
and writes it into .env.

Usage:
    1) Message your bot on Telegram first (send anything — /start works).
    2) python setup_chat_id.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Windows cp1252 console can't print unicode arrows etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _write_chat_id(env_path: Path, chat_id: int) -> None:
    text = env_path.read_text(encoding="utf-8")
    if re.search(r"^TELEGRAM_CHAT_ID=.*$", text, flags=re.M):
        text = re.sub(r"^TELEGRAM_CHAT_ID=.*$", f"TELEGRAM_CHAT_ID={chat_id}", text, flags=re.M)
    else:
        text = text.rstrip() + f"\nTELEGRAM_CHAT_ID={chat_id}\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"Wrote TELEGRAM_CHAT_ID={chat_id} to .env")


def main() -> int:
    root = Path(__file__).resolve().parent
    env_path = root / ".env"
    load_dotenv(env_path)

    # Manual override: `python setup_chat_id.py 123456789`
    if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit():
        _write_chat_id(env_path, int(sys.argv[1]))
        return 0

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN missing in .env")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    print(f"Calling {url}...")
    r = httpx.get(url, timeout=20.0)
    if r.status_code != 200:
        print(f"Telegram returned {r.status_code}: {r.text[:300]}")
        return 1

    data = r.json()
    if not data.get("ok"):
        print(f"Telegram error: {data}")
        return 1

    updates = data.get("result", [])
    if not updates:
        print("No updates found. Try one of these:")
        print("  A) Open a DIRECT chat with your bot (not from BotFather),")
        print("     type any text (e.g. 'hi') and press Send. Then rerun.")
        print("  B) Message @userinfobot on Telegram - it replies with your")
        print("     numeric ID. Paste it as TELEGRAM_CHAT_ID in .env manually.")
        print("  C) Pass it directly: python setup_chat_id.py <chat_id>")
        return 1

    chat_ids: list[tuple[int, str]] = []
    for upd in updates:
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None:
            continue
        label = chat.get("title") or chat.get("username") or chat.get("first_name") or "?"
        chat_ids.append((int(cid), str(label)))

    if not chat_ids:
        print("No chat found in updates. Send a message to the bot first.")
        return 1

    latest_id, latest_label = chat_ids[-1]
    print(f"Found chat: {latest_label} -> id={latest_id}")
    _write_chat_id(env_path, latest_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
