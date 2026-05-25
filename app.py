from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="GoldBot | XAUUSD Realtime Dashboard",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


GOLD = "#d7a84f"
GOLD_SOFT = "#f3d083"
BG = "#080705"
PANEL = "#15100a"
PANEL_2 = "#20160a"
TEXT = "#f6ead0"
MUTED = "#a99670"
RED = "#ef5b5b"
GREEN = "#42d392"


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


MARKET_SYMBOLS = {
    "gold": ("GC=F", "Gold Futures", "", 1.0),
    "dxy": ("DX-Y.NYB", "DXY", "", 1.0),
    "us10y": ("^TNX", "US10Y Yield", "%", 0.1),
}

APP_TZ = ZoneInfo("Asia/Bangkok")
FALLBACK_SYMBOLS = {
    "GC=F": ["GC=F", "XAUUSD=X", "GLD"],
    "DX-Y.NYB": ["DX-Y.NYB", "DX=F", "UUP"],
    "^TNX": ["^TNX", "IEF"],
}
LOAD_PERIOD = "1mo"
LOAD_INTERVAL = "1h"
PERSISTENT_CACHE_PATH = Path(__file__).with_name(".goldbot_market_cache.pkl")


def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            html, body, [data-testid="stAppViewContainer"] {{
                background:
                    radial-gradient(circle at 18% 0%, rgba(215, 168, 79, 0.18), transparent 28%),
                    linear-gradient(135deg, #080705 0%, #0e0b07 42%, #130d05 100%);
                color: {TEXT};
                font-family: Inter, sans-serif;
            }}

            [data-testid="stHeader"] {{
                background: transparent;
            }}

            [data-testid="stToolbar"] {{
                right: 1rem;
            }}

            .block-container {{
                padding-top: 1.4rem;
                padding-bottom: 2rem;
                max-width: 1480px;
            }}

            h1, h2, h3, h4, p, span, label {{
                color: {TEXT};
                letter-spacing: 0;
            }}

            .gold-title {{
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                gap: 1rem;
                padding: 1rem 0 1.15rem;
                border-bottom: 1px solid rgba(215, 168, 79, 0.2);
                margin-bottom: 1rem;
            }}

            .gold-title h1 {{
                margin: 0;
                font-size: clamp(2rem, 4vw, 4.7rem);
                line-height: 0.95;
                color: {GOLD_SOFT};
                font-weight: 800;
            }}

            .gold-title p {{
                margin: 0.35rem 0 0;
                color: {MUTED};
                font-size: 1rem;
            }}

            .status-pill {{
                border: 1px solid rgba(215, 168, 79, 0.38);
                color: {GOLD_SOFT};
                background: rgba(215, 168, 79, 0.08);
                padding: 0.55rem 0.85rem;
                border-radius: 999px;
                font-size: 0.86rem;
                white-space: nowrap;
            }}

            .panel {{
                background: linear-gradient(180deg, rgba(32, 22, 10, 0.95), rgba(16, 12, 8, 0.96));
                border: 1px solid rgba(215, 168, 79, 0.22);
                border-radius: 8px;
                padding: 1rem;
                min-height: 138px;
                box-shadow: 0 18px 44px rgba(0, 0, 0, 0.26);
            }}

            .panel h3 {{
                color: {GOLD_SOFT};
                font-size: 0.96rem;
                text-transform: uppercase;
                margin: 0 0 0.8rem;
                font-weight: 800;
            }}

            .metric-value {{
                font-size: 1.65rem;
                font-weight: 800;
                line-height: 1.1;
                color: {TEXT};
            }}

            .metric-caption {{
                margin-top: 0.4rem;
                color: {MUTED};
                font-size: 0.88rem;
            }}

            .signal-buy {{ color: {GREEN}; }}
            .signal-sell {{ color: {RED}; }}
            .signal-neutral {{ color: {GOLD_SOFT}; }}

            .zone-row {{
                display: grid;
                grid-template-columns: minmax(96px, 0.9fr) 1.2fr minmax(72px, 0.7fr);
                gap: 0.6rem;
                align-items: center;
                padding: 0.7rem 0;
                border-bottom: 1px solid rgba(215, 168, 79, 0.12);
            }}

            .zone-row:last-child {{ border-bottom: 0; }}
            .zone-label {{ color: {MUTED}; font-size: 0.86rem; }}
            .zone-price {{ color: {TEXT}; font-weight: 700; }}
            .zone-tag {{
                justify-self: end;
                color: {BG};
                background: {GOLD};
                border-radius: 999px;
                padding: 0.22rem 0.5rem;
                font-size: 0.75rem;
                font-weight: 800;
            }}

            div[data-testid="stMetric"] {{
                background: linear-gradient(180deg, rgba(32, 22, 10, 0.95), rgba(16, 12, 8, 0.96));
                border: 1px solid rgba(215, 168, 79, 0.22);
                border-radius: 8px;
                padding: 0.9rem 1rem;
            }}

            div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
                color: {TEXT};
            }}

            .stButton > button {{
                background: {GOLD};
                color: {BG};
                border: 0;
                border-radius: 6px;
                font-weight: 800;
                min-height: 2.6rem;
            }}

            .stButton > button:hover {{
                background: {GOLD_SOFT};
                color: {BG};
            }}

            iframe {{
                border-radius: 8px;
            }}

            @media (max-width: 760px) {{
                .gold-title {{
                    align-items: flex-start;
                    flex-direction: column;
                }}

                .zone-row {{
                    grid-template-columns: 1fr;
                }}

                .zone-tag {{
                    justify-self: start;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def clean_market_data(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.rename(columns=str.title)
    required = ["Open", "High", "Low", "Close"]
    return data[[column for column in required + ["Volume"] if column in data.columns]].dropna()


def yfinance_history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    return clean_market_data(yf.Ticker(symbol).history(period=period, interval=interval))


@st.cache_data(ttl=55, show_spinner=False)
def load_market_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str, str, str]:
    del period, interval
    failed_symbols: list[str] = []
    symbol_chain = FALLBACK_SYMBOLS.get(ticker, [ticker])

    for symbol in symbol_chain:
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


def market_status(latest_timestamp: Optional[pd.Timestamp], interval: str, is_cached: bool) -> str:
    if is_cached:
        return "CACHE"
    if latest_timestamp is None:
        return "OFFLINE"

    timestamp = pd.Timestamp(latest_timestamp)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    max_age = pd.Timedelta(hours=3)
    age = pd.Timestamp.now(tz="UTC") - timestamp
    return "LIVE" if age <= max_age else "MARKET CLOSED"


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
    memory_cache = st.session_state.get("market_cache", {})
    persistent_cache = load_persistent_market_cache()
    cached = memory_cache.get(ticker) or persistent_cache.get(ticker)
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


def snapshot(
    ticker: str,
    label: str,
    period: str = "5d",
    interval: str = "15m",
    display_multiplier: float = 1.0,
) -> MarketSnapshot:
    data, resolved_ticker, exception_text, resolved_interval = load_market_data(ticker, period, interval)

    if data.empty or "Close" not in data:
        cached_snapshot = get_cached_snapshot(ticker, label, exception_text, resolved_ticker)
        if cached_snapshot is not None:
            return cached_snapshot
        return MarketSnapshot(
            ticker,
            label,
            None,
            None,
            None,
            data,
            True,
            None,
            None,
            exception_text,
            resolved_ticker,
            "OFFLINE",
        )

    close = data["Close"].dropna()
    raw_value = float(close.iloc[-1])
    price = raw_value * display_multiplier
    previous = (float(close.iloc[-2]) * display_multiplier) if len(close) > 1 else price
    change_pct = ((price - previous) / previous * 100) if previous else 0.0
    updated_at = datetime.now(APP_TZ)
    latest_timestamp = pd.Timestamp(close.index[-1])
    status = market_status(latest_timestamp, resolved_interval, is_cached=False)

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


def resample_ohlc(data: pd.DataFrame, rule: str) -> pd.DataFrame:
    if data.empty:
        return data

    ohlc = data.resample(rule).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        }
    )
    return ohlc.dropna()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def atr(data: pd.DataFrame, length: int = 14) -> pd.Series:
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(length).mean()


def h4_bias(data: pd.DataFrame) -> tuple[str, str, str]:
    h4 = resample_ohlc(data, "4h")
    if len(h4) < 30:
        return "Neutral", "signal-neutral", "Waiting for enough H4 candles"

    close = h4["Close"]
    fast = ema(close, 20)
    slow = ema(close, 50)
    last_close = close.iloc[-1]
    previous_high = h4["High"].iloc[-6:-1].max()
    previous_low = h4["Low"].iloc[-6:-1].min()

    if last_close > fast.iloc[-1] > slow.iloc[-1] and last_close > previous_high:
        return "Bullish", "signal-buy", "Price holds above H4 EMA stack and recent range high"
    if last_close < fast.iloc[-1] < slow.iloc[-1] and last_close < previous_low:
        return "Bearish", "signal-sell", "Price trades below H4 EMA stack and recent range low"
    if fast.iloc[-1] > slow.iloc[-1]:
        return "Bullish Lean", "signal-buy", "H4 trend is positive, waiting for expansion"
    if fast.iloc[-1] < slow.iloc[-1]:
        return "Bearish Lean", "signal-sell", "H4 trend is negative, waiting for expansion"
    return "Neutral", "signal-neutral", "H4 structure is compressed"


def m15_entry(data: pd.DataFrame) -> tuple[str, str, str]:
    if len(data) < 60:
        return "Wait", "signal-neutral", "Waiting for enough M15 candles"

    close = data["Close"]
    fast = ema(close, 9)
    slow = ema(close, 21)
    range_high = data["High"].iloc[-12:-1].max()
    range_low = data["Low"].iloc[-12:-1].min()
    last_close = close.iloc[-1]

    if fast.iloc[-1] > slow.iloc[-1] and last_close > range_high:
        return "Long Setup", "signal-buy", "M15 momentum broke above the short-term range"
    if fast.iloc[-1] < slow.iloc[-1] and last_close < range_low:
        return "Short Setup", "signal-sell", "M15 momentum broke below the short-term range"
    if fast.iloc[-1] > slow.iloc[-1]:
        return "Long Watch", "signal-buy", "Momentum is positive, wait for sweep or pullback"
    if fast.iloc[-1] < slow.iloc[-1]:
        return "Short Watch", "signal-sell", "Momentum is negative, wait for sweep or pullback"
    return "Wait", "signal-neutral", "No clean M15 trigger"


def rolling_correlation(left: pd.DataFrame, right: pd.DataFrame, window: int = 96) -> Optional[float]:
    if left.empty or right.empty:
        return None

    frame = pd.concat(
        [
            left["Close"].pct_change().rename("left"),
            right["Close"].pct_change().rename("right"),
        ],
        axis=1,
    ).dropna()

    if len(frame) < max(12, window // 2):
        return None

    return float(frame["left"].rolling(min(window, len(frame))).corr(frame["right"]).iloc[-1])


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

    clean_zones = []
    for label, price, tag in zones:
        if np.isfinite(price):
            clean_zones.append((label, price, tag))
    return clean_zones[:5]


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


def tradingview_widget() -> None:
    widget_html = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <style>
            html, body, .tradingview-widget-container {
              width: 100%;
              height: 100%;
              margin: 0;
              background: #080705;
              overflow: hidden;
              font-family: Inter, Arial, sans-serif;
            }

            .tradingview-widget-copyright {
              height: 32px;
              display: flex;
              align-items: center;
              padding-left: 10px;
              box-sizing: border-box;
              border-top: 1px solid rgba(215,168,79,0.18);
            }
          </style>
        </head>
        <body>
        <div class="tradingview-widget-container" style="height:650px;width:100%">
          <div id="tradingview_xauusd" style="height:calc(100% - 32px);width:100%"></div>
          <div class="tradingview-widget-copyright">
            <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
              <span style="color:#d7a84f">Track XAUUSD on TradingView</span>
            </a>
          </div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
            new TradingView.widget({
              autosize: true,
              symbol: "OANDA:XAUUSD",
              interval: "15",
              timezone: "Etc/UTC",
              theme: "dark",
              style: "1",
              locale: "en",
              toolbar_bg: "#080705",
              enable_publishing: false,
              hide_side_toolbar: false,
              allow_symbol_change: true,
              studies: ["STD;EMA", "STD;RSI"],
              container_id: "tradingview_xauusd"
            });
          </script>
        </div>
        </body>
        </html>
        """
    st.iframe(f"data:text/html;charset=utf-8,{quote(widget_html)}", height=680, width="stretch")


def mini_line_chart(data: pd.DataFrame, title: str, color: str = GOLD) -> go.Figure:
    fig = go.Figure()
    if not data.empty:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["Close"],
                mode="lines",
                line=dict(color=color, width=2),
                hovertemplate="%{y:.3f}<extra></extra>",
            )
        )
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT, size=13)),
        height=210,
        margin=dict(l=8, r=8, t=34, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(gridcolor="rgba(215,168,79,0.12)", zeroline=False),
    )
    return fig


def render_signal_panel(title: str, signal: str, css_class: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="panel">
            <h3>{title}</h3>
            <div class="metric-value {css_class}">{signal}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_zone_panel(title: str, rows: list[tuple]) -> None:
    body_parts = []
    if rows:
        for row in rows:
            if isinstance(row, str):
                body_parts.append(row)
                continue

            label = str(row[0]) if len(row) > 0 else ""
            tag = str(row[-1]) if len(row) > 2 else ""
            price_text = ""

            if len(row) >= 4:
                try:
                    price_text = f"{float(row[1]):,.2f} - {float(row[2]):,.2f}"
                except (TypeError, ValueError):
                    price_text = f"{row[1]} - {row[2]}"
            elif len(row) >= 2:
                try:
                    price_text = f"{float(row[1]):,.2f}"
                except (TypeError, ValueError):
                    price_text = str(row[1])

            body_parts.append(
                '<div class="zone-row">'
                f'<div class="zone-label">{label}</div>'
                f'<div class="zone-price">{price_text}</div>'
                f'<div class="zone-tag">{tag}</div>'
                "</div>"
            )
    else:
        body_parts.append('<div class="metric-caption">Waiting for enough live data.</div>')

    html = f'<div class="panel"><h3>{title}</h3>{"".join(body_parts)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_price_metrics(gold: MarketSnapshot, dxy: MarketSnapshot, us10y: MarketSnapshot) -> None:
    columns = st.columns(3)
    for column, item, suffix in zip(columns, [gold, dxy, us10y], ["", "", "%"]):
        price = "N/A" if item.price is None else f"{item.price:,.2f}{suffix}"
        delta = None if item.change_pct is None else f"{item.change_pct:+.2f}%"
        column.metric(item.label, price, delta)
        if item.updated_at is not None:
            cached = " (cached)" if item.is_cached else ""
            column.caption(f"{item.status} | Updated {item.updated_at:%Y-%m-%d %H:%M:%S} ICT{cached}")
        else:
            column.caption(f"{item.status} | Waiting for first live update")


def format_debug_value(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:,.6f}"


def format_debug_timestamp(value: Optional[pd.Timestamp]) -> str:
    if value is None:
        return "N/A"

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(APP_TZ)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")


def normalize_debug_timestamp(value: pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def render_data_debug(gold: MarketSnapshot, dxy: MarketSnapshot, us10y: MarketSnapshot) -> None:
    snapshots = [gold, dxy, us10y]

    st.markdown(
        """
        <div class="panel">
            <h3>DATA DEBUG</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    debug_columns = st.columns(4)
    debug_columns[0].metric("GC=F raw value", format_debug_value(gold.raw_value))
    debug_columns[1].metric("DX-Y.NYB raw value", format_debug_value(dxy.raw_value))
    debug_columns[2].metric("^TNX raw value", format_debug_value(us10y.raw_value))

    latest_timestamps = [
        normalize_debug_timestamp(item.latest_timestamp)
        for item in snapshots
        if item.latest_timestamp is not None
    ]
    latest_timestamp = max(latest_timestamps) if latest_timestamps else None
    debug_columns[3].metric("latest timestamp", format_debug_timestamp(latest_timestamp))

    debug_rows = []
    for item in snapshots:
        debug_rows.append(
            {
                "symbol": item.ticker,
                "resolved_symbol": item.resolved_ticker or item.ticker,
                "raw_value": item.raw_value,
                "latest_timestamp": format_debug_timestamp(item.latest_timestamp),
                "status": item.status,
                "cached": item.is_cached,
                "exception": item.exception_text,
            }
        )
    st.dataframe(pd.DataFrame(debug_rows), width="stretch", hide_index=True)


def realtime_fragment(func):
    if hasattr(st, "fragment"):
        return st.fragment(run_every="60s")(func)
    return func


@realtime_fragment
def render_realtime_dashboard() -> None:
    gold_symbol, gold_label, _, gold_multiplier = MARKET_SYMBOLS["gold"]
    dxy_symbol, dxy_label, _, dxy_multiplier = MARKET_SYMBOLS["dxy"]
    us10y_symbol, us10y_label, _, us10y_multiplier = MARKET_SYMBOLS["us10y"]

    gold = snapshot(gold_symbol, gold_label, display_multiplier=gold_multiplier)
    dxy = snapshot(dxy_symbol, dxy_label, display_multiplier=dxy_multiplier)
    us10y = snapshot(us10y_symbol, us10y_label, display_multiplier=us10y_multiplier)

    render_price_metrics(gold, dxy, us10y)

    st.write("")
    chart_col, side_col = st.columns([1.7, 1], gap="large")

    with chart_col:
        tradingview_widget()

    with side_col:
        h4_signal, h4_class, h4_caption = h4_bias(gold.data)
        m15_signal, m15_class, m15_caption = m15_entry(gold.data)
        dxy_corr = rolling_correlation(gold.data, dxy.data)
        us10y_corr = rolling_correlation(gold.data, us10y.data)

        top_a, top_b = st.columns(2)
        with top_a:
            render_signal_panel("H4 Bias", h4_signal, h4_class, h4_caption)
        with top_b:
            render_signal_panel("M15 Entry", m15_signal, m15_class, m15_caption)

        corr_a, corr_b = st.columns(2)
        with corr_a:
            dxy_text = "N/A" if dxy_corr is None else f"{dxy_corr:+.2f}"
            dxy_class = "signal-sell" if dxy_corr and dxy_corr < -0.25 else "signal-neutral"
            render_signal_panel("DXY Correlation", dxy_text, dxy_class, "Rolling M15 return correlation")
        with corr_b:
            yield_text = "N/A" if us10y_corr is None else f"{us10y_corr:+.2f}"
            yield_class = "signal-sell" if us10y_corr and us10y_corr < -0.25 else "signal-neutral"
            render_signal_panel("US10Y Yield", yield_text, yield_class, "Gold sensitivity to yield moves")

        render_zone_panel("Liquidity Sweep Zone", liquidity_zones(gold.data))

    st.write("")
    section_a, section_b, section_c = st.columns([1, 1, 1], gap="large")
    with section_a:
        render_zone_panel("Order Block", order_blocks(gold.data))
    with section_b:
        render_zone_panel("Fair Value Gap", fair_value_gaps(gold.data))
    with section_c:
        st.plotly_chart(mini_line_chart(dxy.data.tail(120), "DXY Intraday", "#8fb9ff"), width="stretch")
        st.plotly_chart(mini_line_chart(us10y.data.tail(120), "US10Y Intraday", "#d7a84f"), width="stretch")

    st.write("")
    st.write("")

show_debug = st.sidebar.toggle(
    "Debug Mode",
    value=False
)

if show_debug:
    render_data_debug(
        gold,
        dxy,
        us10y
    )


def main() -> None:
    inject_theme()

    left, right = st.columns([0.78, 0.22])
    with left:
        st.markdown(
            """
            <div class="gold-title">
                <div>
                    <h1>XAUUSD Realtime</h1>
                    <p>Smart money dashboard for H4 direction, M15 execution, dollar pressure, yields, liquidity and imbalance zones.</p>
                </div>
                <div class="status-pill">Data refresh: 60s</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Refresh market data", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    render_realtime_dashboard()

    st.caption(
        "For execution support only. Signals are rule-based from delayed public market data and are not financial advice."
    )


if __name__ == "__main__":
    main()
