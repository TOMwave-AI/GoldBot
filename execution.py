from __future__ import annotations

from typing import Optional

import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    class _ATR:
        @staticmethod
        def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
            high_low = high - low
            high_close = (high - close.shift()).abs()
            low_close = (low - close.shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            return true_range.rolling(length).mean()

    ta = _ATR()


def volatility_buffer(data: pd.DataFrame) -> Optional[float]:
    """Return the latest ATR value used as the execution volatility buffer."""
    if data.empty or len(data) < 14:
        return None

    atr = ta.atr(
        data.High,
        data.Low,
        data.Close,
        length=14,
    )

    if atr.empty or pd.isna(atr.iloc[-1]):
        return None
    return float(atr.iloc[-1])


def execution_levels(data: pd.DataFrame, bias: str, entry_signal: str) -> dict[str, Optional[float]]:
    """Build short-side planning levels from the ATR volatility buffer."""
    del bias, entry_signal

    if data.empty or "Close" not in data:
        return {"current": None, "entry": None, "sl": None, "tp1": None, "tp2": None}

    current = float(data["Close"].iloc[-1])
    buffer = volatility_buffer(data)
    if buffer is None:
        recent = data.tail(24)
        buffer = float((recent["High"] - recent["Low"]).median()) if len(recent) else current * 0.001

    entry = current
    sl = entry + buffer * 1.5
    tp1 = entry - buffer * 1.0
    tp2 = entry - buffer * 2.0

    return {"current": current, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2}
