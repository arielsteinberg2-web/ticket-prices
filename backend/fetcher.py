import datetime
import logging
import time
from typing import Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
MAX_RETRIES = 3
PAGE_SIZE = 200


def fetch_events(keyword: str, classification: str, api_key: str) -> list[dict]:
    """
    Fetch all events matching keyword + classification from Ticketmaster.
    Handles pagination automatically. Returns list of raw event dicts.
    """
    events = []
    page = 0

    while True:
        resp = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(BASE_URL, params={
                    "apikey": api_key,
                    "keyword": keyword,
                    "classificationName": classification,
                    "size": PAGE_SIZE,
                    "page": page,
                }, timeout=10)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Rate limited. Waiting %ds before retry.", wait)
                    time.sleep(wait)
                    resp = None
                    continue
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error("Failed to fetch page %d for '%s': %s", page, keyword, e)
                    return events
                time.sleep(2 ** attempt)

        if resp is None:
            logger.error("All retries exhausted for page %d of '%s'", page, keyword)
            return events

        data = resp.json()
        page_events = data.get("_embedded", {}).get("events", [])
        events.extend(page_events)

        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages", 1)
        if page >= total_pages - 1:
            break
        page += 1

    return events


def extract_lowest_price(event: dict) -> Optional[float]:
    """Return the lowest min price across all priceRanges, or None if absent."""
    price_ranges = event.get("priceRanges", [])
    if not price_ranges:
        return None
    mins = [pr.get("min") for pr in price_ranges if pr.get("min") is not None]
    return min(mins) if mins else None


def build_event_record(event: dict, category: str) -> dict:
    """
    Convert a raw Ticketmaster event dict into a flat record suitable for DB upsert.
    Returns dict with keys: ticketmaster_id, name, category, event_date, venue, city, lowest_price.
    lowest_price is None if no price available.
    """
    venues = event.get("_embedded", {}).get("venues", [])
    venue_name = venues[0].get("name") if venues else None
    city = venues[0].get("city", {}).get("name") if venues else None

    date_str = event.get("dates", {}).get("start", {}).get("dateTime")
    event_date = None
    if date_str:
        try:
            event_date = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass

    return {
        "ticketmaster_id": event["id"],
        "name": event.get("name", "Unknown"),
        "category": category,
        "event_date": event_date,
        "venue": venue_name,
        "city": city,
        "lowest_price": extract_lowest_price(event),
    }
