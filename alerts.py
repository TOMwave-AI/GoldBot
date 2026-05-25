from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
)
LAST_ALERT_PATH = Path(__file__).with_name("last_alert.json")
COOLDOWN_SECONDS = 45 * 60


def send_alert(message):
    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=10,
    )


def load_last_alert_state() -> dict[str, Any]:
    if not LAST_ALERT_PATH.exists():
        return {}

    try:
        return json.loads(LAST_ALERT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_alert_state(state: dict[str, Any]) -> None:
    LAST_ALERT_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def alert_signature(payload: dict[str, Any]) -> str:
    watched = {
        "h4_bias": payload.get("h4_bias"),
        "m15_entry": payload.get("m15_entry"),
        "ai_bias": payload.get("ai_bias"),
        "liquidity": payload.get("liquidity"),
        "macro": payload.get("macro"),
        "stop_hunt": payload.get("stop_hunt"),
    }
    print(
        "SIGNATURE PAYLOAD:",
        watched
    )

    return json.dumps(
        watched,
        sort_keys=True,
        default=str
    )

def cooldown_ready(state: dict[str, Any]) -> bool:
    last_sent_at = state.get("sent_at")
    if not last_sent_at:
        return True

    try:
        sent_at = datetime.fromisoformat(last_sent_at)
    except ValueError:
        return True

    return (datetime.now(timezone.utc) - sent_at).total_seconds() >= COOLDOWN_SECONDS

def should_send_auto_alert(
    payload: dict
) -> bool:

    state = load_last_alert_state()

    signature = alert_signature(
        payload
    )

    if state.get(
        "signature"
    ) == signature:

        return False

    return cooldown_ready(
        state
    )


def mark_alert_sent(payload: dict[str, Any], message: str) -> None:
    save_last_alert_state(
        {
            "signature": alert_signature(payload),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "message": message,
        }
    )


def telegram_configured() -> bool:
    """Return True when Telegram alert environment variables are present."""
    return bool(BOT_TOKEN and CHAT_ID)


def alert_status() -> str:
    if telegram_configured():
        return "Telegram ready"
    return "Telegram disabled"
