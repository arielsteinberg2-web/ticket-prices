"""
Multi-factor ticket price prediction engine.

Scoring factors:
  1. Days until event — urgency
  2. Price position vs own history — is it cheap right now?
  3. Trend direction (exponentially weighted regression)
  4. Recent momentum — is the trend reversing?
  5. Trend strength — how steep is the change?
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
    prices: list of (date, lowest_price) sorted ascending.
    event_date: the event date, used for urgency.
    Returns None if fewer than 3 data points.
    """
    if len(prices) < 3:
        return None

    today = datetime.date.today()
    base_date = prices[0][0]

    X = np.array([(p[0] - base_date).days for p in prices], dtype=float)
    y = np.array([p[1] for p in prices], dtype=float)

    current_price = float(y[-1])
    price_mean = float(y.mean())
    price_min = float(y.min())
    price_max = float(y.max())
    price_range = price_max - price_min

    # ── 1. Overall trend (exponential weights — recent data matters more) ──────
    n = len(X)
    weights = np.exp(np.linspace(0, 2, n))          # older → lower weight
    slope = _weighted_slope(X, y, weights)           # $/day

    # Normalize slope as % of mean price per day → scale-independent
    slope_pct_per_day = (slope / price_mean * 100) if price_mean > 0 else 0

    FLAT_THRESHOLD = 0.25  # less than 0.25%/day change → flat
    if abs(slope_pct_per_day) < FLAT_THRESHOLD:
        trend = "flat"
    elif slope_pct_per_day > 0:
        trend = "rising"
    else:
        trend = "falling"

    # ── 2. Recent momentum (last ~33% of data, min 3 points) ─────────────────
    recent_n = max(3, n // 3)
    recent_y = y[-recent_n:]
    recent_X = X[-recent_n:]
    recent_weights = np.exp(np.linspace(0, 2, recent_n))
    recent_slope = _weighted_slope(recent_X, recent_y, recent_weights)
    recent_slope_pct = (recent_slope / price_mean * 100) if price_mean > 0 else 0

    momentum_reversing = (
        (trend == "rising" and recent_slope_pct < -FLAT_THRESHOLD) or
        (trend == "falling" and recent_slope_pct > FLAT_THRESHOLD)
    )

    # ── 3. Price position vs own history ──────────────────────────────────────
    # 0 = at all-time low, 1 = at all-time high
    price_position = (current_price - price_min) / price_range if price_range > 5 else 0.5

    # ── 4. Days until event ────────────────────────────────────────────────────
    days_until_event: Optional[int] = None
    if event_date:
        days_until_event = (event_date - today).days

    # ── 5. 7-day price projection ──────────────────────────────────────────────
    predicted_price_7d = round(current_price + slope * 7, 2)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORING — each factor contributes to a score:
    #   ≥ 4  → BUY NOW
    #   2-3  → BUY SOON
    #   ≤ 1  → WAIT
    # ═══════════════════════════════════════════════════════════════════════════
    score = 0

    # Factor A: Urgency from days until event
    if days_until_event is not None:
        if days_until_event <= 0:
            score += 5   # event is today/past
        elif days_until_event <= 14:
            score += 4   # < 2 weeks — must buy now
        elif days_until_event <= 30:
            score += 3   # < 1 month — getting urgent
        elif days_until_event <= 60:
            score += 1   # 1-2 months — some urgency
        # > 60 days → no urgency boost
    else:
        score += 1       # unknown date — slight lean toward buying

    # Factor B: Price position (cheap = buy, expensive = wait)
    if price_position <= 0.15:
        score += 3       # at or near all-time low — excellent entry
    elif price_position <= 0.35:
        score += 2       # below average — good entry
    elif price_position <= 0.55:
        score += 1       # average — neutral
    elif price_position >= 0.80:
        score -= 1       # near all-time high — consider waiting

    # Factor C: Trend direction
    if trend == "falling":
        # Prices dropping — wait for the bottom UNLESS event is near
        if days_until_event is not None and days_until_event <= 30:
            score += 1   # near event: falling prices won't last, buy soon
        else:
            score -= 1   # plenty of time: let prices fall further
    elif trend == "rising":
        # Prices rising — buy before they go higher
        if days_until_event is not None and days_until_event <= 45:
            score += 1   # rising + event closing in = buy soon
        else:
            score -= 1   # rising but far out — might stabilize
    elif trend == "flat":
        score += 1       # stable prices — safe to buy anytime

    # Factor D: Momentum reversal (trend changing direction)
    if momentum_reversing:
        if trend == "rising" and recent_slope_pct < -FLAT_THRESHOLD:
            score += 1   # was rising, now dipping — could be a dip to buy
        elif trend == "falling" and recent_slope_pct > FLAT_THRESHOLD:
            score -= 1   # was falling, now bouncing — might fall more

    # Factor E: Trend strength penalty for strong rises (wait it out)
    if slope_pct_per_day > 1.5 and (days_until_event is None or days_until_event > 45):
        score -= 1       # aggressively rising and event is far — definitely wait

    # ── Map score to recommendation ────────────────────────────────────────────
    if score >= 4:
        recommendation = "BUY NOW"
    elif score >= 2:
        recommendation = "BUY SOON"
    else:
        recommendation = "WAIT"

    return Prediction(
        trend=trend,
        predicted_price_7d=predicted_price_7d,
        recommendation=recommendation,
        slope=round(slope, 4),
        score=score,
    )
