import datetime
import pytest
from unittest.mock import patch, MagicMock
from backend.fetcher import fetch_events, extract_lowest_price, build_event_record


def _make_tm_event(tm_id, name, min_price=100.0, max_price=500.0, date_str="2026-06-22T20:00:00Z"):
    return {
        "id": tm_id,
        "name": name,
        "dates": {"start": {"dateTime": date_str}},
        "_embedded": {"venues": [{"name": "MetLife Stadium", "city": {"name": "East Rutherford"}}]},
        "priceRanges": [{"type": "standard", "currency": "USD", "min": min_price, "max": max_price}],
    }


def test_extract_lowest_price_standard():
    event = _make_tm_event("x", "Test", min_price=150.0)
    assert extract_lowest_price(event) == 150.0


def test_extract_lowest_price_multiple_ranges():
    event = _make_tm_event("x", "Test")
    event["priceRanges"] = [
        {"min": 200.0, "max": 400.0},
        {"min": 90.0, "max": 300.0},
    ]
    assert extract_lowest_price(event) == 90.0


def test_extract_lowest_price_missing_returns_none():
    event = {"id": "x", "name": "Test"}
    assert extract_lowest_price(event) is None


def test_build_event_record():
    event = _make_tm_event("tm_abc", "USA vs Mexico", min_price=210.0)
    record = build_event_record(event, category="world_cup")
    assert record["ticketmaster_id"] == "tm_abc"
    assert record["name"] == "USA vs Mexico"
    assert record["category"] == "world_cup"
    assert record["lowest_price"] == 210.0
    assert record["venue"] == "MetLife Stadium"
    assert record["city"] == "East Rutherford"
    assert isinstance(record["event_date"], datetime.datetime)


def test_fetch_events_single_page():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "_embedded": {"events": [_make_tm_event("t1", "Game 1"), _make_tm_event("t2", "Game 2")]},
        "page": {"totalPages": 1, "number": 0},
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200

    with patch("backend.fetcher.requests.get", return_value=mock_response) as mock_get:
        results = fetch_events("FIFA World Cup 2026", "Sports", "fake_key")
        assert len(results) == 2
        assert mock_get.call_count == 1


def test_fetch_events_multiple_pages():
    def side_effect(url, params, timeout):
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        mock.status_code = 200
        page_num = params.get("page", 0)
        mock.json.return_value = {
            "_embedded": {"events": [_make_tm_event(f"t{page_num}", f"Game {page_num}")]},
            "page": {"totalPages": 2, "number": page_num},
        }
        return mock

    with patch("backend.fetcher.requests.get", side_effect=side_effect):
        results = fetch_events("FIFA World Cup 2026", "Sports", "fake_key")
        assert len(results) == 2


def test_fetch_events_no_embedded_returns_empty():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"page": {"totalPages": 1}}

    with patch("backend.fetcher.requests.get", return_value=mock_response):
        results = fetch_events("test", "Sports", "fake_key")
        assert results == []
