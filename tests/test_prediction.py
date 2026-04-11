import datetime
import pytest
from backend.prediction import predict, Prediction

_BASE = datetime.date(2026, 1, 1)

def _prices(values: list[float]) -> list[tuple[datetime.date, float]]:
    return [(_BASE + datetime.timedelta(days=i), v) for i, v in enumerate(values)]


def test_returns_none_for_fewer_than_3_points():
    assert predict(_prices([100.0, 110.0])) is None


def test_falling_trend():
    result = predict(_prices([300.0, 280.0, 260.0, 240.0, 220.0]))
    assert result.trend == "falling"
    assert result.slope < 0


def test_rising_trend():
    result = predict(_prices([100.0, 120.0, 140.0, 160.0, 180.0]))
    assert result.trend == "rising"
    assert result.slope > 0


def test_flat_trend():
    result = predict(_prices([200.0, 201.0, 200.0, 199.0, 200.0]))
    assert result.trend == "flat"


def test_predicted_price_7d_is_float():
    result = predict(_prices([100.0, 110.0, 120.0]))
    assert isinstance(result.predicted_price_7d, float)


def test_recommendation_buy_now_when_falling():
    result = predict(_prices([300.0, 280.0, 260.0, 240.0, 220.0]))
    assert result.recommendation == "BUY NOW"


def test_recommendation_buy_now_when_flat():
    result = predict(_prices([200.0, 201.0, 200.0, 199.0, 200.0]))
    assert result.recommendation == "BUY NOW"


def test_recommendation_buy_now_when_rising_and_event_soon():
    event_date = datetime.date.today() + datetime.timedelta(days=15)
    result = predict(_prices([100.0, 120.0, 140.0, 160.0, 180.0]), event_date=event_date)
    assert result.recommendation == "BUY NOW"


def test_recommendation_wait_when_rising_and_event_far():
    event_date = datetime.date.today() + datetime.timedelta(days=90)
    result = predict(_prices([100.0, 120.0, 140.0, 160.0, 180.0]), event_date=event_date)
    assert result.recommendation == "WAIT"


def test_recommendation_buy_soon_when_rising_and_no_event_date():
    result = predict(_prices([100.0, 120.0, 140.0, 160.0, 180.0]))
    assert result.recommendation == "BUY SOON"
