import datetime
from dataclasses import dataclass
from typing import Optional
import numpy as np
from sklearn.linear_model import LinearRegression

SLOPE_THRESHOLD = 0.5  # $/day — below this magnitude is considered "flat"
EVENT_URGENCY_DAYS = 30  # event within this many days → "BUY NOW" even if rising


@dataclass
class Prediction:
    trend: str                        # "rising" | "falling" | "flat"
    predicted_price_7d: Optional[float]
    recommendation: str               # "BUY NOW" | "BUY SOON" | "WAIT"
    slope: float                      # $/day


def predict(
    prices: list[tuple[datetime.date, float]],
    event_date: Optional[datetime.date] = None,
) -> Optional[Prediction]:
    """
    Fit a linear regression on (day_number, price) pairs.
    Returns None if fewer than 3 data points.

    prices: list of (date, lowest_price) tuples sorted ascending by date.
    event_date: optional date of the event, used for urgency check.
    """
    if len(prices) < 3:
        return None

    base_date = prices[0][0]
    X = np.array([(p[0] - base_date).days for p in prices], dtype=float).reshape(-1, 1)
    y = np.array([p[1] for p in prices], dtype=float)

    model = LinearRegression().fit(X, y)
    slope = float(model.coef_[0])

    latest_day = float((prices[-1][0] - base_date).days)
    predicted_price_7d = float(model.predict([[latest_day + 7]])[0])

    if slope > SLOPE_THRESHOLD:
        trend = "rising"
    elif slope < -SLOPE_THRESHOLD:
        trend = "falling"
    else:
        trend = "flat"

    # Recommendation logic
    days_until_event = None
    if event_date:
        days_until_event = (event_date - datetime.date.today()).days

    if trend == "falling":
        recommendation = "BUY NOW"  # prices dropping — good time to buy
    elif trend == "flat":
        recommendation = "BUY NOW"  # won't get better
    elif trend == "rising":
        if days_until_event is not None and days_until_event <= EVENT_URGENCY_DAYS:
            recommendation = "BUY NOW"   # rising but event is soon — no time to wait
        elif days_until_event is None:
            recommendation = "BUY SOON"  # rising, unknown urgency
        else:
            recommendation = "WAIT"      # rising but event is far — prices may stabilize
    else:
        recommendation = "BUY SOON"

    return Prediction(
        trend=trend,
        predicted_price_7d=round(predicted_price_7d, 2),
        recommendation=recommendation,
        slope=round(slope, 4),
    )
