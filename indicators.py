from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from config import GOLD, TEXT


def resample_ohlc(data: pd.DataFrame, rule: str) -> pd.DataFrame:
    if data.empty:
        return data

    return data.resample(rule).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


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
