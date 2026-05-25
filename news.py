from __future__ import annotations


HIGH_IMPACT = {
    "FOMC",
    "NFP",
    "CPI",
    "Fed Speech",
}


def trading_lock(event):
    return event in HIGH_IMPACT
