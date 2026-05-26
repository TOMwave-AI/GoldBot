from __future__ import annotations

from datetime import datetime
import hashlib
import json
from outcome import update_trade_result
from journal import log_trade
from urllib.parse import quote

import streamlit as st

from ai_bias import ai_bias
from alerts import alert_status, mark_alert_sent, send_alert, should_send_auto_alert, telegram_configured
from config import BG, GOLD, GOLD_SOFT, GREEN, MARKET_SYMBOLS, MUTED, RED, TEXT
from debug import render_data_debug
from execution import execution_levels
from indicators import h4_bias, m15_entry, mini_line_chart
from liquidity import fair_value_gaps, liquidity_zones, order_blocks, stop_hunt_detector
from macro import macro_pressure, real_yield_signal, rolling_correlation, snapshot
from news import trading_lock

import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)

st.set_page_config(
    page_title="GoldBot | XAUUSD Realtime Dashboard",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_theme() -> None:
    """Keep the established dark gold dashboard styling."""
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
            [data-testid="stHeader"] {{ background: transparent; }}
            [data-testid="stToolbar"] {{ right: 1rem; }}
            .block-container {{ padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1480px; }}
            h1, h2, h3, h4, p, span, label {{ color: {TEXT}; letter-spacing: 0; }}
            .gold-title {{
                display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem;
                padding: 1rem 0 1.15rem; border-bottom: 1px solid rgba(215, 168, 79, 0.2);
                margin-bottom: 1rem;
            }}
            .gold-title h1 {{
                margin: 0; font-size: clamp(2rem, 4vw, 4.7rem); line-height: 0.95;
                color: {GOLD_SOFT}; font-weight: 800;
            }}
            .gold-title p {{ margin: 0.35rem 0 0; color: {MUTED}; font-size: 1rem; }}
            .status-pill {{
                border: 1px solid rgba(215, 168, 79, 0.38); color: {GOLD_SOFT};
                background: rgba(215, 168, 79, 0.08); padding: 0.55rem 0.85rem;
                border-radius: 999px; font-size: 0.86rem; white-space: nowrap;
            }}
            .panel {{
                background: linear-gradient(180deg, rgba(32, 22, 10, 0.95), rgba(16, 12, 8, 0.96));
                border: 1px solid rgba(215, 168, 79, 0.22); border-radius: 8px; padding: 1rem;
                min-height: 138px; box-shadow: 0 18px 44px rgba(0, 0, 0, 0.26);
            }}
            .panel h3 {{
                color: {GOLD_SOFT}; font-size: 0.96rem; text-transform: uppercase;
                margin: 0 0 0.8rem; font-weight: 800;
            }}
            .metric-value {{ font-size: 1.65rem; font-weight: 800; line-height: 1.1; color: {TEXT}; }}
            .metric-caption {{ margin-top: 0.4rem; color: {MUTED}; font-size: 0.88rem; }}
            .signal-buy {{ color: {GREEN}; }}
            .signal-sell {{ color: {RED}; }}
            .signal-neutral {{ color: {GOLD_SOFT}; }}
            .zone-row {{
                display: grid; grid-template-columns: minmax(96px, 0.9fr) 1.2fr minmax(72px, 0.7fr);
                gap: 0.6rem; align-items: center; padding: 0.7rem 0;
                border-bottom: 1px solid rgba(215, 168, 79, 0.12);
            }}
            .zone-row:last-child {{ border-bottom: 0; }}
            .zone-label {{ color: {MUTED}; font-size: 0.86rem; }}
            .zone-price {{ color: {TEXT}; font-weight: 700; }}
            .zone-tag {{
                justify-self: end; color: {BG}; background: {GOLD}; border-radius: 999px;
                padding: 0.22rem 0.5rem; font-size: 0.75rem; font-weight: 800;
            }}
            div[data-testid="stMetric"] {{
                background: linear-gradient(180deg, rgba(32, 22, 10, 0.95), rgba(16, 12, 8, 0.96));
                border: 1px solid rgba(215, 168, 79, 0.22); border-radius: 8px; padding: 0.9rem 1rem;
            }}
            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: {TEXT}; }}
            .stButton > button {{
                background: {GOLD}; color: {BG}; border: 0; border-radius: 6px;
                font-weight: 800; min-height: 2.6rem;
            }}
            .stButton > button:hover {{ background: {GOLD_SOFT}; color: {BG}; }}
            iframe {{ border-radius: 8px; }}
            @media (max-width: 760px) {{
                .gold-title {{ align-items: flex-start; flex-direction: column; }}
                .zone-row {{ grid-template-columns: 1fr; }}
                .zone-tag {{ justify-self: start; }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def tradingview_widget() -> None:
    widget_html = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <style>
            html, body, .tradingview-widget-container {
              width: 100%; height: 100%; margin: 0; background: #080705;
              overflow: hidden; font-family: Inter, Arial, sans-serif;
            }
            .tradingview-widget-copyright {
              height: 32px; display: flex; align-items: center; padding-left: 10px;
              box-sizing: border-box; border-top: 1px solid rgba(215,168,79,0.18);
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


def render_signal_panel(title: str, signal: str, css_class: str, caption: str) -> None:
    st.markdown(
        f'<div class="panel"><h3>{title}</h3><div class="metric-value {css_class}">{signal}</div>'
        f'<div class="metric-caption">{caption}</div></div>',
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
            price_text = _format_range(row[1], row[2]) if len(row) >= 4 else _format_price(row[1]) if len(row) >= 2 else ""
            body_parts.append(
                '<div class="zone-row">'
                f'<div class="zone-label">{label}</div>'
                f'<div class="zone-price">{price_text}</div>'
                f'<div class="zone-tag">{tag}</div>'
                "</div>"
            )
    else:
        body_parts.append('<div class="metric-caption">Waiting for enough live data.</div>')
    st.markdown(f'<div class="panel"><h3>{title}</h3>{"".join(body_parts)}</div>', unsafe_allow_html=True)


def render_execution_panel(levels: dict[str, float | None], locked: bool = False) -> None:
    rows = [
        ("Current price", levels.get("current"), "Now"),
        ("Entry", None if locked else levels.get("entry"), "Plan"),
        ("SL", None if locked else levels.get("sl"), "Risk"),
        ("TP1", None if locked else levels.get("tp1"), "Target"),
        ("TP2", None if locked else levels.get("tp2"), "Target"),
    ]
    render_zone_panel("Execution", rows)


def build_alert_payload(
    h4_signal: str,
    m15_signal: str,
    ai_signal: str,
    levels: dict[str, float | None],
    macro_signal: str,
    stop_signal: str,
    liquidity_rows: list[tuple],
) -> dict:
    return {
        "h4_bias": h4_signal,
        "m15_entry": m15_signal,
        "entry": _format_price(levels.get("entry")),
        "sl": _format_price(levels.get("sl")),
        "tp1": _format_price(levels.get("tp1")),
        "tp2": _format_price(levels.get("tp2")),
        "ai_bias": ai_signal,
        "liquidity": format_liquidity_summary(liquidity_rows),
        "macro": macro_signal,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_telegram_message(payload: dict) -> str:
    return (
        "🔥 XAUUSD ALERT\n\n"
        f"Bias: {payload['h4_bias']} / {payload['m15_entry']}\n"
        f"Entry: {payload['entry']}\n"
        f"SL: {payload['sl']}\n"
        f"TP1: {payload['tp1']}\n"
        f"TP2: {payload['tp2']}\n"
        f"AI Bias: {payload['ai_bias']}\n"
        f"Liquidity: {payload['liquidity']}\n"
        f"Macro: {payload['macro']}\n"
        f"Time: {payload['time']}"
    )


def render_telegram_controls() -> bool:
    auto_alert_enabled = st.toggle(
    "AUTO ALERT",
    value=st.session_state.get(
        "auto_alert_enabled",
        False
    ),
    key="auto_alert_enabled"
)
    if telegram_configured():
        st.success("Telegram ready")
    else:
        st.warning("Telegram not configured")

    if st.button("Manual SEND NOW", width="stretch"):
        try:
            message = st.session_state.get("telegram_message", "🔥 XAUUSD ALERT\n\nNo signal calculated yet.")
            payload = st.session_state.get("alert_payload")

            ok=send_telegram_alert(message)
            
            if ok:                

                if payload:
                    mark_alert_sent(payload, message)
                    
                    log_trade(
                        payload
                    )

                    print(
                        "LOG TRADE RUN",
                        payload
                    )
                     

            st.success("Telegram signal sent")

        except Exception as e:
            print(
                "TELEGRAM ERROR",
                e
            )

            st.error(
                f"Telegram failed: {e}"
            )
        return auto_alert_enabled


def render_price_metrics(gold, dxy, us10y) -> None:
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


def render_header() -> None:
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


def render_sidebar() -> tuple[bool, str, bool, bool]:
    with st.sidebar:
        st.header("GoldBot")
        debug_enabled = st.toggle("Debug", value=False)
        st.markdown("---")
        st.subheader("NEWS CONTROL")
        news_event = st.selectbox("High Impact News", ["None", "FOMC", "NFP", "CPI", "Fed Speech"])
        news_locked = trading_lock(news_event)
        if news_locked:
            st.error("HIGH IMPACT EVENT")
            st.warning("TRADING DISABLED")
        st.markdown("---")
        st.subheader("TELEGRAM")
        auto_alert_enabled = render_telegram_controls()
        status = st.session_state.get("telegram_status")
        if status:
            st.caption(status)
        st.caption(alert_status())
        st.caption("TODO: MT5 bridge, broker symbol mapping, guarded execution.")
    return debug_enabled, news_event, news_locked, auto_alert_enabled


def realtime_fragment(func):
    if hasattr(st, "fragment"):
        return st.fragment(run_every="60s")(func)
    return func


@realtime_fragment
def render_realtime_dashboard(debug_enabled: bool, news_event: str, news_locked: bool, auto_alert_enabled: bool) -> None:
    gold_symbol, gold_label, _, gold_multiplier = MARKET_SYMBOLS["gold"]
    dxy_symbol, dxy_label, _, dxy_multiplier = MARKET_SYMBOLS["dxy"]
    us10y_symbol, us10y_label, _, us10y_multiplier = MARKET_SYMBOLS["us10y"]

    gold = snapshot(gold_symbol, gold_label, display_multiplier=gold_multiplier)
    dxy = snapshot(dxy_symbol, dxy_label, display_multiplier=dxy_multiplier)
    us10y = snapshot(us10y_symbol, us10y_label, display_multiplier=us10y_multiplier)

    h4_signal, h4_class, h4_caption = h4_bias(gold.data)
    m15_signal, m15_class, m15_caption = m15_entry(gold.data)
    dxy_corr = rolling_correlation(gold.data, dxy.data)
    us10y_corr = rolling_correlation(gold.data, us10y.data)
    macro_signal, macro_class, macro_caption = macro_pressure(dxy_corr, us10y_corr)
    real_yield_text, real_yield_class, real_yield_caption = real_yield_signal(us10y.price)
    stop_signal, stop_class, stop_caption = stop_hunt_detector(gold.data)
    ai_signal, ai_confidence = ai_bias(h4_signal, dxy_corr, us10y_corr, stop_signal, macro_signal)
    ai_class = "signal-sell" if "SELL" in ai_signal else "signal-buy" if "BUY" in ai_signal else "signal-neutral"
    status_text = "LOCKED" if news_locked else "SAFE"
    status_class = "signal-sell" if news_locked else "signal-buy"
    status_caption = f"{news_event} lock active" if news_locked else "No high-impact event selected"
    levels = execution_levels(gold.data, h4_signal, m15_signal)
    liquidity_rows = liquidity_zones(gold.data)

    alert_payload = build_alert_payload(h4_signal, m15_signal, ai_signal, levels, macro_signal, stop_signal, liquidity_rows)
    telegram_message = build_telegram_message(alert_payload)
    st.session_state["alert_payload"] = alert_payload
    st.session_state["telegram_message"] = telegram_message

    if "auto_initialized" not in st.session_state:
        st.session_state["auto_initialized"] = True

    if auto_alert_enabled and telegram_configured():

        try:

            if should_send_auto_alert(
                alert_payload
            ):

                ok = send_telegram_alert(
                    telegram_message
                )

                if ok:

                    mark_alert_sent(
                        alert_payload,
                        telegram_message
                    )
                    log_trade(
                        alert_payload
                    )

                    st.session_state[
                        "telegram_status"
                    ] = "Auto alert sent"

        except Exception as e:

            st.session_state[
            "telegram_status"
        ] = str(e)
            
    if gold.price:

        update_trade_result(
        gold.price
        )

    render_price_metrics(gold, dxy, us10y)

    st.write("")
    chart_col, side_col = st.columns([1.7, 1], gap="large")
    with chart_col:
        tradingview_widget()

    with side_col:
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

        render_signal_panel("Macro Pressure", macro_signal, macro_class, macro_caption)
        render_signal_panel("Real Yield", real_yield_text, real_yield_class, real_yield_caption)
        render_signal_panel("Stop Hunt", stop_signal, stop_class, stop_caption)
        render_signal_panel("AI Bias", ai_signal, ai_class, f"Confidence {ai_confidence:.0%}")
        render_signal_panel("NEWS STATUS", status_text, status_class, status_caption)
        render_zone_panel("Liquidity Sweep Zone", liquidity_rows)

    st.write("")
    section_a, section_b, section_c = st.columns([1, 1, 1], gap="large")
    with section_a:
        render_zone_panel("Order Block", order_blocks(gold.data))
    with section_b:
        render_zone_panel("Fair Value Gap", fair_value_gaps(gold.data))
    with section_c:
        render_execution_panel(levels, locked=news_locked)

    st.write("")
    macro_a, macro_b = st.columns([1, 1], gap="large")
    with macro_a:
        st.plotly_chart(mini_line_chart(dxy.data.tail(120), "DXY Intraday", "#8fb9ff"), width="stretch")
    with macro_b:
        st.plotly_chart(mini_line_chart(us10y.data.tail(120), "US10Y Intraday", "#d7a84f"), width="stretch")

    if debug_enabled:
        st.write("")
        render_data_debug(gold, dxy, us10y)


def _format_price(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _format_range(low, high) -> str:
    return f"{_format_price(low)} - {_format_price(high)}"


def format_liquidity_summary(rows: list[tuple]) -> str:
    if not rows:
        return "No active liquidity zone"
    first = rows[0]
    if len(first) >= 3:
        return f"{first[0]} {_format_price(first[1])} {first[-1]}"
    if len(first) >= 2:
        return f"{first[0]} {_format_price(first[1])}"
    return str(first[0])
def _format_liquidity_summary(rows: list[tuple]) -> str:
    if not rows:
        return "No active liquidity zone"

    first = rows[0]

    if len(first) >= 3:
        return f"{first[0]} {_format_price(first[1])} {first[-1]}"

    if len(first) >= 2:
        return f"{first[0]} {_format_price(first[1])}"

    return str(first[0])


def send_telegram_alert(message):

    if not TELEGRAM_BOT_TOKEN:
        return False

    if not TELEGRAM_CHAT_ID:
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        f"/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:

        r = requests.post(
            url,
            json=payload,
            timeout=10
        )

        r.raise_for_status()

        return True

    except Exception as e:

        st.sidebar.error(str(e))

        return False


def main() -> None:

    inject_theme()
    debug_enabled, news_event, news_locked, auto_alert_enabled = render_sidebar()
    render_header()
    render_realtime_dashboard(debug_enabled, news_event, news_locked, auto_alert_enabled)
    st.caption("For execution support only. Signals are rule-based.")


if __name__ == "__main__":
    main()
