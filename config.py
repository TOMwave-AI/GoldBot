from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo


GOLD = "#d7a84f"
GOLD_SOFT = "#f3d083"
BG = "#080705"
TEXT = "#f6ead0"
MUTED = "#a99670"
RED = "#ef5b5b"
GREEN = "#42d392"

APP_TZ = ZoneInfo("Asia/Bangkok")
LOAD_PERIOD = "1mo"
LOAD_INTERVAL = "1h"
PERSISTENT_CACHE_PATH = Path(__file__).with_name(".goldbot_market_cache.pkl")

MARKET_SYMBOLS = {
    "gold": ("GC=F", "Gold Futures", "", 1.0),
    "dxy": ("DX-Y.NYB", "DXY", "", 1.0),
    "us10y": ("^TNX", "US10Y Yield", "%", 0.1),
}

FALLBACK_SYMBOLS = {
    "GC=F": ["GC=F", "XAUUSD=X", "GLD"],
    "DX-Y.NYB": ["DX-Y.NYB", "DX=F", "UUP"],
    "^TNX": ["^TNX", "IEF"],
}

TELEGRAM_ENV_KEYS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

# TODO: MT5 integration
# - Add MT5 account/session configuration.
# - Map dashboard execution levels to broker symbol names.
# - Add order preview, risk sizing, and guarded trade execution.
