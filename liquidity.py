from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import atr


def liquidity_zones(data: pd.DataFrame) -> list[tuple[str, float, str]]:
    if data.empty or len(data) < 30:
        return []

    recent = data.tail(80)
    previous = data.iloc[-81:-1] if len(data) > 81 else data.iloc[:-1]
    latest = data.iloc[-1]
    zones = [
        ("Buy-side liquidity", float(recent["High"].max()), "BSL"),
        ("Sell-side liquidity", float(recent["Low"].min()), "SSL"),
        ("Asian range high", float(data.between_time("00:00", "06:00")["High"].tail(32).max()), "Asia H"),
        ("Asian range low", float(data.between_time("00:00", "06:00")["Low"].tail(32).min()), "Asia L"),
    ]

    if not previous.empty:
        prev_high = previous["High"].tail(40).max()
        prev_low = previous["Low"].tail(40).min()
        if latest["High"] > prev_high and latest["Close"] < prev_high:
            zones.insert(0, ("Active sweep", float(prev_high), "High swept"))
        elif latest["Low"] < prev_low and latest["Close"] > prev_low:
            zones.insert(0, ("Active sweep", float(prev_low), "Low swept"))

    return [(label, price, tag) for label, price, tag in zones if np.isfinite(price)][:5]


def order_blocks(data: pd.DataFrame) -> list[tuple[str, float, float, str]]:
    if data.empty or len(data) < 30:
        return []

    candles = data.tail(80).copy()
    candles["Body"] = (candles["Close"] - candles["Open"]).abs()
    candles["Atr"] = atr(candles, 14)
    blocks: list[tuple[str, float, float, str]] = []

    for idx in range(3, len(candles) - 1):
        candle = candles.iloc[idx]
        next_candle = candles.iloc[idx + 1]
        displacement = abs(next_candle["Close"] - next_candle["Open"])
        threshold = next_candle["Atr"] if np.isfinite(next_candle["Atr"]) else candles["Body"].median()

        if candle["Close"] < candle["Open"] and next_candle["Close"] > next_candle["Open"] and displacement > threshold:
            blocks.append(("Bullish OB", float(candle["Low"]), float(candle["High"]), "Demand"))
        elif candle["Close"] > candle["Open"] and next_candle["Close"] < next_candle["Open"] and displacement > threshold:
            blocks.append(("Bearish OB", float(candle["Low"]), float(candle["High"]), "Supply"))

    return blocks[-4:][::-1]


def fair_value_gaps(data: pd.DataFrame) -> list[tuple[str, float, float, str]]:
    if data.empty or len(data) < 10:
        return []

    gaps: list[tuple[str, float, float, str]] = []
    candles = data.tail(90)
    for idx in range(2, len(candles)):
        left = candles.iloc[idx - 2]
        current = candles.iloc[idx]
        if current["Low"] > left["High"]:
            gaps.append(("Bullish FVG", float(left["High"]), float(current["Low"]), "Imbalance"))
        elif current["High"] < left["Low"]:
            gaps.append(("Bearish FVG", float(current["High"]), float(left["Low"]), "Imbalance"))
    return gaps[-4:][::-1]


def stop_hunt_detector(data: pd.DataFrame, tolerance_ratio: float = 0.0008) -> tuple[str, str, str]:
    """Detect equal highs/lows and sweep risk from recent candles."""
    if data.empty or len(data) < 20:
        return "Waiting", "signal-neutral", "Need more candles for stop hunt scan"

    recent = data.tail(30)
    price = float(recent["Close"].iloc[-1])
    tolerance = max(price * tolerance_ratio, 0.01)
    highs = recent["High"].tail(12)
    lows = recent["Low"].tail(12)
    equal_high = (highs.max() - highs.nlargest(2).iloc[-1]) <= tolerance
    equal_low = (lows.nsmallest(2).iloc[-1] - lows.min()) <= tolerance

    latest = recent.iloc[-1]
    prev_high = recent["High"].iloc[:-1].max()
    prev_low = recent["Low"].iloc[:-1].min()
    swept_high = latest["High"] > prev_high and latest["Close"] < prev_high
    swept_low = latest["Low"] < prev_low and latest["Close"] > prev_low

    if swept_high:
        return "High Sweep Risk", "signal-sell", "Buy-side liquidity was probed and rejected"
    if swept_low:
        return "Low Sweep Risk", "signal-buy", "Sell-side liquidity was probed and rejected"
    if equal_high and equal_low:
        return "Equal H/L", "signal-neutral", "Both equal highs and equal lows are nearby"
    if equal_high:
        return "Equal High", "signal-sell", "Buy stops are clustered above recent highs"
    if equal_low:
        return "Equal Low", "signal-buy", "Sell stops are clustered below recent lows"
    return "Normal", "signal-neutral", "No immediate stop hunt structure"
