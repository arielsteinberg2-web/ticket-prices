"""
Multi-factor ticket price prediction engine.

Scoring is price-first; urgency acts as a floor on the recommendation,
not a score booster. This prevents "BUY NOW" from being triggered by
time pressure alone when prices are at all-time highs or still falling.

Requires at least 7 unique days of price data.
"""
import datetime
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Prediction:
    trend: str                        # "rising" | "falling" | "flat"
    predicted_price_7d: Optional[float]
    recommendation: str               # "BUY NOW" | "BUY SOON" | "WAIT"
    slope: float                      # $/day (for chart trendline)
    score: int                        # raw score for debugging
    confidence: str = "low"           # "low" | "medium" | "high"


def _weighted_slope(X: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    """Weighted linear regression slope ($/unit X)."""
    w_sum = weights.sum()
    x_mean = (weights * X).sum() / w_sum
    y_mean = (weights * y).sum() / w_sum
    num = (weights * (X - x_mean) * (y - y_mean)).sum()
    den = (weights * (X - x_mean) ** 2).sum()
    return float(num / den) if den != 0 else 0.0


def predict(
    prices: list[tuple[datetime.date, float]],
    event_date: Optional[datetime.date] = None,
) -> Optional["Prediction"]:
    """
    prices: list of (date, lowest_price) — may contain multiple per day.
    event_date: used for urgency floor.
    Returns None if fewer than 7 unique days of data.
    """
    # Deduplicate to one price per day (keep last)
    daily: dict[datetime.date, float] = {}
    for d, p in prices:
        daily[d] = p
    daily_prices = sorted(daily.items())

    if len(daily_prices) < 7:
        return None

    today = datetime.date.today()
    base_date = daily_prices[0][0]

    X = np.array([(d - base_date).days for d, _ in daily_prices], dtype=float)
    y = np.array([p for _, p in daily_prices], dtype=float)

    n = len(X)
    current_price = float(y[-1])
    price_mean = float(y.mean())
    price_min = float(y.min())
    price_max = float(y.max())
    price_range = price_max - price_min
    price_range_pct = (price_range / price_mean * 100) if price_mean > 0 else 0

    # ── Overall trend (exponential weights — recent data matters more) ──────────
    weights = np.exp(np.linspace(0, 2, n))
    slope = _weighted_slope(X, y, weights)
    slope_pct_per_day = (slope / price_mean * 100) if price_mean > 0 else 0

    FLAT_THRESHOLD = 0.25
    if abs(slope_pct_per_day) < FLAT_THRESHOLD:
        trend = "flat"
    elif slope_pct_per_day > 0:
        trend = "rising"
    else:
        trend = "falling"

    # ── Recent momentum (last ~25% of data, min 4 points) ──────────────────────
    recent_n = max(4, n // 4)
    recent_y = y[-recent_n:]
    recent_X = X[-recent_n:]
    recent_weights = np.exp(np.linspace(0, 2, recent_n))
    recent_slope = _weighted_slope(recent_X, recent_y, recent_weights)
    recent_slope_pct = (recent_slope / price_mean * 100) if price_mean > 0 else 0

    momentum_reversing = (
        (trend == "rising" and recent_slope_pct < -FLAT_THRESHOLD) or
        (trend == "falling" and recent_slope_pct > FLAT_THRESHOLD)
    )
    trend_consistent = not momentum_reversing

    # ── Price position vs own history ──────────────────────────────────────────
    price_position = (current_price - price_min) / price_range if price_range > 5 else 0.5

    # ── Days until event ────────────────────────────────────────────────────────
    days_until_event: Optional[int] = None
    if event_date:
        days_until_event = (event_date - today).days

    # ── 7-day price projection (use recent slope — more predictive) ─────────────
    proj_n = max(4, min(n, 14))
    proj_y = y[-proj_n:]
    proj_X = X[-proj_n:]
    proj_weights = np.exp(np.linspace(0, 2, proj_n))
    proj_slope = _weighted_slope(proj_X, proj_y, proj_weights)
    predicted_price_7d = round(current_price + proj_slope * 7, 2)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORING — price quality first, urgency applied as a floor afterward
    # ═══════════════════════════════════════════════════════════════════════════
    score = 0

    # Factor A: Price position (is it cheap right now?)
    if price_position <= 0.15:
        score += 3       # near all-time low — excellent entry
    elif price_position <= 0.35:
        score += 2       # below average — good entry
    elif price_position <= 0.55:
        score += 1       # average
    elif price_position >= 0.80:
        score -= 1       # near all-time high — wait

    # Factor B: Trend direction
    if trend == "falling":
        if days_until_event is not None and days_until_event <= 21:
            score += 1   # near event: falling won't last, buy soon
        else:
            score -= 1   # plenty of time: let it fall further
    elif trend == "rising":
        if days_until_event is not None and days_until_event <= 45:
            score += 1   # rising + closing in = buy before it's higher
        else:
            score -= 1   # rising but far out — may stabilize
    elif trend == "flat":
        score += 1       # stable — safe to buy anytime

    # Factor C: Momentum reversal
    if trend == "rising" and recent_slope_pct < -FLAT_THRESHOLD:
        score += 1       # was rising, now dipping — dip to buy
    elif trend == "falling" and recent_slope_pct > FLAT_THRESHOLD:
        score -= 1       # was falling, now bouncing — might fall more

    # Factor D: Strong rising trend + far event = definitely wait
    if slope_pct_per_day > 1.5 and (days_until_event is None or days_until_event > 45):
        score -= 1

    # ── Map score to base recommendation ───────────────────────────────────────
    if score >= 4:
        recommendation = "BUY NOW"
    elif score >= 2:
        recommendation = "BUY SOON"
    else:
        recommendation = "WAIT"

    # ── Urgency floor (lifts recommendation, never lowers it) ──────────────────
    if days_until_event is not None:
        if days_until_event <= 7:
            recommendation = "BUY NOW"          # must act now regardless of price
        elif days_until_event <= 21 and recommendation == "WAIT":
            recommendation = "BUY SOON"         # < 3 weeks — can't wait indefinitely
        elif days_until_event <= 45 and recommendation == "WAIT" and trend != "falling":
            recommendation = "BUY SOON"         # < 6 weeks, not actively falling

    # ── Confidence ─────────────────────────────────────────────────────────────
    conf_score = 0
    if n >= 30:
        conf_score += 3
    elif n >= 14:
        conf_score += 2
    elif n >= 7:
        conf_score += 1

    if price_range_pct >= 15:
        conf_score += 2  # meaningful price movement = reliable signal
    elif price_range_pct >= 8:
        conf_score += 1

    if trend_consistent:
        conf_score += 1  # trend not reversing = more reliable

    if conf_score >= 5:
        confidence = "high"
    elif conf_score >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return Prediction(
        trend=trend,
        predicted_price_7d=predicted_price_7d,
        recommendation=recommendation,
        slope=round(slope, 4),
        score=score,
        confidence=confidence,
    )
