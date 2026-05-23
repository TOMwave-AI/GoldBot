# GoldBot

XAUUSD realtime dashboard built with Streamlit, TradingView, and Smart Money Concepts style market panels.

## Features

- TradingView XAUUSD chart
- H4 Bias panel
- M15 Entry panel
- DXY correlation panel
- US10Y yield panel
- Liquidity sweep zone
- Order Block and Fair Value Gap sections
- Dark gold UI theme

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app uses TradingView for the main chart and Yahoo Finance data through `yfinance` for rule-based market panels. Public market data can be delayed depending on the upstream provider.
