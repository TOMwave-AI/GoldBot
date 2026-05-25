from __future__ import annotations


def ai_bias(
    h4_signal,
    dxy_corr,
    us10_corr,
    stop_hunt,
    macro,
):
    score = 0

    if "Bearish" in h4_signal:
        score -= 1

    if dxy_corr and dxy_corr < -0.25:
        score -= 1

    if us10_corr and us10_corr < -0.25:
        score -= 1

    if "Equal High" in stop_hunt:
        score -= 1

    if "Supportive" in macro:
        score += 1

    confidence = abs(score) / 5

    if score <= -3:
        return "STRONG SELL", confidence

    if score >= 2:
        return "STRONG BUY", confidence

    return "NEUTRAL", confidence
