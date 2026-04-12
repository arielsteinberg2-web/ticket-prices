import datetime
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.seatgeek.com/2/events"
PAGE_SIZE = 100
MAX_RETRIES = 3


def fetch_seatgeek_events(keyword: str, client_id: str) -> list[dict]:
    """Fetch all SeatGeek events matching keyword. Returns raw event dicts."""
    events = []
    page = 1

    while True:
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(BASE_URL, params={
                    "q": keyword,
                    "client_id": client_id,
                    "per_page": PAGE_SIZE,
                    "page": page,
                }, timeout=10)
                if resp.status_code == 429:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error("SeatGeek fetch failed for '%s': %s", keyword, e)
                    return events
                import time
                time.sleep(2 ** attempt)

        data = resp.json()
        page_events = data.get("events", [])
        events.extend(page_events)

        meta = data.get("meta", {})
        total = meta.get("total", 0)
        if len(events) >= total or not page_events:
            break
        page += 1

    return events


def extract_seatgeek_price(event: dict) -> Optional[float]:
    """Return the lowest price from SeatGeek stats, or None if unavailable."""
    stats = event.get("stats", {})
    price = stats.get("lowest_price")
    return float(price) if price else None


def build_seatgeek_record(event: dict, category: str) -> dict:
    """Convert a SeatGeek event dict into a flat record for DB matching."""
    venue = event.get("venue", {})
    city = venue.get("city")
    state = venue.get("state")
    city_str = f"{city}, {state}" if city and state else city

    dt_str = event.get("datetime_local")
    event_date = None
    if dt_str:
        try:
            event_date = datetime.datetime.fromisoformat(dt_str)
        except ValueError:
            pass

    return {
        "seatgeek_id": str(event.get("id", "")),
        "name": event.get("title", "Unknown"),
        "category": category,
        "event_date": event_date,
        "venue": venue.get("name"),
        "city": city_str,
        "lowest_price": extract_seatgeek_price(event),
        "url": event.get("url"),
    }
