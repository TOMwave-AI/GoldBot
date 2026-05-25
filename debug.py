from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from config import APP_TZ
from macro import MarketSnapshot


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
    st.markdown('<div class="panel"><h3>DATA DEBUG</h3></div>', unsafe_allow_html=True)

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

    debug_rows = [
        {
            "symbol": item.ticker,
            "resolved_symbol": item.resolved_ticker or item.ticker,
            "raw_value": item.raw_value,
            "latest_timestamp": format_debug_timestamp(item.latest_timestamp),
            "status": item.status,
            "cached": item.is_cached,
            "note": item.exception_text,
        }
        for item in snapshots
    ]
    st.dataframe(pd.DataFrame(debug_rows), width="stretch", hide_index=True)
