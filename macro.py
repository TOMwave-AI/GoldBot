from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf

from config import APP_TZ, FALLBACK_SYMBOLS, LOAD_INTERVAL, LOAD_PERIOD, PERSISTENT_CACHE_PATH


@dataclass
class MarketSnapshot:
    ticker: str
    label: str
    price: Optional[float]
    change_pct: Optional[float]
    updated_at: Optional[datetime]
    data: pd.DataFrame
    is_cached: bool = False
    raw_value: Optional[float] = None
    latest_timestamp: Optional[pd.Timestamp] = None
    exception_text: str = ""
    resolved_ticker: Optional[str] = None
    status: str = "OFFLINE"


def clean_market_data(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance output into a predictable OHLC dataframe."""
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.rename(columns=str.title)
    required = ["Open", "High", "Low", "Close"]
    columns = [column for column in required + ["Volume"] if column in data.columns]
    return data[columns].dropna()


def yfinance_history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    return clean_market_data(yf.Ticker(symbol).history(period=period, interval=interval))


@st.cache_data(ttl=55, show_spinner=False)
def load_market_data(ticker: str, period: str = LOAD_PERIOD, interval: str = LOAD_INTERVAL) -> tuple[pd.DataFrame, str, str, str]:
    """Load yfinance data with symbol fallbacks and compact status notes."""
    del period, interval
    failed_symbols: list[str] = []

    for symbol in FALLBACK_SYMBOLS.get(ticker, [ticker]):
        try:
            data = yfinance_history(symbol, LOAD_PERIOD, LOAD_INTERVAL)
        except Exception:
            failed_symbols.append(symbol)
            continue

        if not data.empty and "Close" in data:
            if symbol != ticker:
                return data, symbol, f"fallback {symbol} used", LOAD_INTERVAL
            return data, symbol, "", LOAD_INTERVAL

        failed_symbols.append(symbol)

    note = f"No yfinance data from: {', '.join(failed_symbols)}" if failed_symbols else "No yfinance data"
    return pd.DataFrame(), ticker, note, LOAD_INTERVAL


def market_status(latest_timestamp: Optional[pd.Timestamp], is_cached: bool) -> str:
    if is_cached:
        return "CACHE"
    if latest_timestamp is None:
        return "OFFLINE"

    timestamp = pd.Timestamp(latest_timestamp)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    age = pd.Timestamp.now(tz="UTC") - timestamp
    return "LIVE" if age <= pd.Timedelta(hours=3) else "MARKET CLOSED"


def load_persistent_market_cache() -> dict:
    if "persistent_market_cache" not in st.session_state:
        if PERSISTENT_CACHE_PATH.exists():
            try:
                st.session_state["persistent_market_cache"] = pd.read_pickle(PERSISTENT_CACHE_PATH)
            except Exception:
                st.session_state["persistent_market_cache"] = {}
        else:
            st.session_state["persistent_market_cache"] = {}
    return st.session_state["persistent_market_cache"]


def save_persistent_market_cache(cache: dict) -> None:
    try:
        pd.to_pickle(cache, PERSISTENT_CACHE_PATH)
    except Exception:
        pass


def get_cached_snapshot(ticker: str, label: str, exception_text: str, resolved_ticker: str) -> Optional[MarketSnapshot]:
    cached = st.session_state.get("market_cache", {}).get(ticker) or load_persistent_market_cache().get(ticker)
    if cached is None:
        return None

    return MarketSnapshot(
        ticker=ticker,
        label=label,
        price=cached["price"],
        change_pct=cached["change_pct"],
        updated_at=cached["updated_at"],
        data=cached["data"],
        is_cached=True,
        raw_value=cached["raw_value"],
        latest_timestamp=cached["latest_timestamp"],
        exception_text=exception_text,
        resolved_ticker=cached.get("resolved_ticker", resolved_ticker),
        status="CACHE",
    )


def snapshot(ticker: str, label: str, display_multiplier: float = 1.0) -> MarketSnapshot:
    data, resolved_ticker, exception_text, _ = load_market_data(ticker)

    if data.empty or "Close" not in data:
        cached_snapshot = get_cached_snapshot(ticker, label, exception_text, resolved_ticker)
        if cached_snapshot is not None:
            return cached_snapshot
        return MarketSnapshot(ticker, label, None, None, None, data, True, None, None, exception_text, resolved_ticker, "OFFLINE")

    close = data["Close"].dropna()
    raw_value = float(close.iloc[-1])
    price = raw_value * display_multiplier
    previous = (float(close.iloc[-2]) * display_multiplier) if len(close) > 1 else price
    change_pct = ((price - previous) / previous * 100) if previous else 0.0
    updated_at = datetime.now(APP_TZ)
    latest_timestamp = pd.Timestamp(close.index[-1])
    status = market_status(latest_timestamp, is_cached=False)

    st.session_state.setdefault("market_cache", {})[ticker] = {
        "price": price,
        "change_pct": change_pct,
        "updated_at": updated_at,
        "data": data,
        "raw_value": raw_value,
        "latest_timestamp": latest_timestamp,
        "resolved_ticker": resolved_ticker,
        "status": status,
    }
    persistent_cache = load_persistent_market_cache()
    persistent_cache[ticker] = st.session_state["market_cache"][ticker]
    save_persistent_market_cache(persistent_cache)

    return MarketSnapshot(
        ticker=ticker,
        label=label,
        price=price,
        change_pct=change_pct,
        updated_at=updated_at,
        data=data,
        raw_value=raw_value,
        latest_timestamp=latest_timestamp,
        exception_text=exception_text,
        resolved_ticker=resolved_ticker,
        status=status,
    )


def rolling_correlation(left: pd.DataFrame, right: pd.DataFrame, window: int = 96) -> Optional[float]:
    if left.empty or right.empty:
        return None

    frame = pd.concat(
        [left["Close"].pct_change().rename("left"), right["Close"].pct_change().rename("right")],
        axis=1,
        sort=False,
    ).dropna()

    if len(frame) < max(12, window // 2):
        return None

    return float(frame["left"].rolling(min(window, len(frame))).corr(frame["right"]).iloc[-1])


def macro_pressure(dxy_corr: Optional[float], us10y_corr: Optional[float]) -> tuple[str, str, str]:
    """Summarize dollar and yield pressure against gold."""
    values = [value for value in (dxy_corr, us10y_corr) if value is not None]
    if not values:
        return "Neutral", "signal-neutral", "Waiting for DXY and US10Y correlation"

    pressure = sum(values) / len(values)
    if pressure <= -0.25:
        return "Gold Supportive", "signal-buy", "Dollar/yield correlation is leaning negative"
    if pressure >= 0.25:
        return "Gold Headwind", "signal-sell", "Dollar/yield correlation is leaning positive"
    return "Mixed", "signal-neutral", "Macro pressure is balanced"


def real_yield_signal(us10_value: Optional[float], inflation: float = 2.5) -> tuple[str, str, str]:
    """Classify gold pressure from estimated real yield."""
    if us10_value is None:
        return "Neutral", "signal-neutral", "Waiting for US10Y yield"

    real_yield = us10_value - inflation

    if real_yield > 2:
        return "Bearish Gold", "signal-sell", f"Real yield {real_yield:.2f}%"

    if real_yield < 1:
        return "Bullish Gold", "signal-buy", f"Real yield {real_yield:.2f}%"

    return "Neutral", "signal-neutral", f"Real yield {real_yield:.2f}%"
