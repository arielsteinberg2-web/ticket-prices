import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def check_token_expiry(token: str) -> None:
    """Decode JWT expiry and warn/email if within 14 days."""
    try:
        import base64, json as _json, datetime as _dt
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get('exp')
        if not exp:
            return
        exp_dt = _dt.datetime.utcfromtimestamp(exp)
        days_left = (exp_dt - _dt.datetime.utcnow()).days
        logger.info("TickPick token expires %s (%d days)", exp_dt.strftime('%Y-%m-%d'), days_left)
        if days_left <= 14:
            logger.warning("TickPick token expires in %d days!", days_left)
            try:
                import os, smtplib
                from email.mime.text import MIMEText
                gmail_user = os.getenv("GMAIL_USER", "")
                gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")
                if gmail_user and gmail_pass:
                    msg = MIMEText(
                        f"Your TickPick auth token expires on {exp_dt.strftime('%B %d, %Y')} ({days_left} days). "
                        f"Update TICKPICK_TOKEN in your .env / Railway environment variables."
                    )
                    msg["Subject"] = f"TickPick token expires in {days_left} days — action required"
                    msg["From"] = gmail_user
                    msg["To"] = gmail_user
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                        s.login(gmail_user, gmail_pass)
                        s.sendmail(gmail_user, gmail_user, msg.as_string())
            except Exception as e:
                logger.error("Failed to send token expiry alert: %s", e)
    except Exception:
        pass  # Don't crash if token parsing fails


BASE_URL = "https://api.tickpick.com/1.0/listings/internal/event-v2"
HEADERS = {
    "client-platform": "web",
    "x-client-id": "tickpick",
    "content-type": "application/json",
}

SITEMAPS = [
    "https://www.tickpick.com/sitemap/concert-1.xml",
    "https://www.tickpick.com/sitemap/concert-2.xml",
    "https://www.tickpick.com/sitemap/sports.xml",
    "https://www.tickpick.com/sitemap/theater.xml",
    "https://www.tickpick.com/sitemap/other.xml",
]

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "tickpick_sitemap_cache.json")
_SITEMAP_CACHE: Optional[list] = None
_CACHE_LOADED_AT: Optional[datetime] = None

# Words to ignore when building keyword list from event names
_STOP_WORDS = {
    "the", "a", "an", "and", "or", "vs", "vs.", "at", "in", "on",
    "of", "for", "to", "with", "feat", "ft", "presents", "presents:",
    "tickets", "tour", "live", "concert", "show",
}


def extract_tickpick_id(url: str) -> Optional[str]:
    """Extract numeric event ID from a TickPick URL."""
    match = re.search(r'/(\d{5,8})(?:[/?]|$)', url)
    return match.group(1) if match else None


def fetch_tickpick_price(tickpick_id: str, token: str, quantity: int = 1) -> Optional[float]:
    """Return the lowest listing price for a TickPick event for the given quantity, or None."""
    result = fetch_tickpick_prices_all_qty(tickpick_id, token)
    return result.get(quantity)


def fetch_tickpick_prices_all_qty(tickpick_id: str, token: str) -> dict:
    """Return lowest prices for quantities 1-6 in a single API call. Returns {qty: price}."""
    try:
        resp = requests.get(
            f"{BASE_URL}/{tickpick_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("TickPick listings returned %d for event %s", resp.status_code, tickpick_id)
            return {}
        listings = resp.json().get("listings", [])
        # Exclude parking
        ticket_listings = [
            l for l in listings
            if l.get("p") is not None
            and "pk" not in (l.get("d") or [])
            and "PARKING" not in (l.get("r") or "").upper()
        ]
        result = {}
        for qty in range(1, 7):
            prices = [l["p"] for l in ticket_listings if l.get("q", 1) >= qty]
            if prices:
                result[qty] = min(prices)
        return result
    except Exception as e:
        logger.error("TickPick fetch failed for event %s: %s", tickpick_id, e)
        return {}


# ---------------------------------------------------------------------------
# Sitemap-based event discovery
# ---------------------------------------------------------------------------

def _parse_tickpick_url(url: str) -> Optional[dict]:
    """Parse a TickPick sitemap URL → {slug, date, id}.

    URL format: /buy-[slug]-[M]-[D]-[YY]-[time]/[id]/
    e.g.  /buy-shakira-tickets-ubs-arena-7-23-26-7pm/7846961/
    """
    id_match = re.search(r'/(\d{5,8})/?$', url)
    if not id_match:
        return None
    tickpick_id = id_match.group(1)

    # Find M-D-YY-TIME pattern (last occurrence, so greedy slug doesn't matter)
    date_matches = re.findall(r'(\d{1,2})-(\d{1,2})-(\d{2})-\d+[ap]m', url)
    if not date_matches:
        return None
    m_str, d_str, yy_str = date_matches[-1]
    try:
        evt_date = date(2000 + int(yy_str), int(m_str), int(d_str))
    except ValueError:
        return None

    # Slug is everything between /buy- and the date segment
    slug_match = re.search(r'/buy-(.+)-\d{1,2}-\d{1,2}-\d{2}-\d+[ap]m/', url)
    slug = slug_match.group(1) if slug_match else ""

    return {"slug": slug, "date": evt_date.isoformat(), "id": tickpick_id}


def _load_cache() -> bool:
    """Load sitemap cache from disk into memory. Returns True if cache is fresh."""
    global _SITEMAP_CACHE, _CACHE_LOADED_AT
    if not os.path.exists(_CACHE_PATH):
        return False
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data["cached_at"])
        if (datetime.utcnow() - cached_at).total_seconds() > 86400:
            return False
        _SITEMAP_CACHE = data["events"]
        _CACHE_LOADED_AT = cached_at
        logger.info("Loaded %d TickPick events from cache", len(_SITEMAP_CACHE))
        return True
    except Exception as e:
        logger.warning("Could not load sitemap cache: %s", e)
        return False


def _save_cache(events: list):
    global _SITEMAP_CACHE, _CACHE_LOADED_AT
    _SITEMAP_CACHE = events
    _CACHE_LOADED_AT = datetime.utcnow()
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"cached_at": _CACHE_LOADED_AT.isoformat(), "events": events}, f)
        logger.info("Saved %d TickPick events to sitemap cache", len(events))
    except Exception as e:
        logger.warning("Could not save sitemap cache: %s", e)


def refresh_sitemap_cache() -> int:
    """Download all TickPick sitemaps and rebuild the cache. Returns event count."""
    events = []
    for sitemap_url in SITEMAPS:
        try:
            resp = requests.get(
                sitemap_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=60,
            )
            if resp.status_code != 200:
                logger.warning("Sitemap %s returned %d", sitemap_url, resp.status_code)
                continue
            urls = re.findall(
                r'<loc>(https://www\.tickpick\.com/buy-[^<]+)</loc>',
                resp.text,
            )
            for url in urls:
                parsed = _parse_tickpick_url(url)
                if parsed:
                    events.append(parsed)
            logger.info("Sitemap %s: %d events", sitemap_url.split("/")[-1], len(urls))
        except Exception as e:
            logger.warning("Failed to fetch sitemap %s: %s", sitemap_url, e)

    if events:
        _save_cache(events)
    return len(events)


def _get_sitemap_events() -> list:
    """Return cached sitemap events, loading or refreshing as needed."""
    global _SITEMAP_CACHE
    if _SITEMAP_CACHE is not None:
        return _SITEMAP_CACHE
    if _load_cache():
        return _SITEMAP_CACHE
    # Cache missing or stale — fetch fresh
    refresh_sitemap_cache()
    return _SITEMAP_CACHE or []


def _name_to_keywords(event_name: str) -> list[str]:
    """Convert an event name to a list of lowercase slug keywords."""
    words = re.findall(r'[a-z0-9]+', event_name.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def find_tickpick_id(event_name: str, event_date) -> Optional[str]:
    """Find a TickPick event ID by matching name keywords + date against sitemaps.

    Args:
        event_name: Human-readable event name (e.g., "Shakira" or "FIFA World Cup…")
        event_date: datetime.date or datetime.datetime of the event

    Returns:
        TickPick event ID string, or None if no confident match found.
    """
    if isinstance(event_date, datetime):
        evt_date = event_date.date()
    elif isinstance(event_date, date):
        evt_date = event_date
    else:
        return None

    events = _get_sitemap_events()
    if not events:
        logger.warning("Sitemap cache empty — cannot auto-discover TickPick ID")
        return None

    keywords = _name_to_keywords(event_name)
    if not keywords:
        return None

    primary_kw = keywords[0]  # Must appear in slug

    best_id: Optional[str] = None
    best_score = 0

    for evt in events:
        slug = evt["slug"]
        # Primary keyword must be present
        if primary_kw not in slug:
            continue

        # Date must match exactly (or ±1 day for timezone safety)
        try:
            evt_d = date.fromisoformat(evt["date"])
        except Exception:
            continue
        if abs((evt_d - evt_date).days) > 1:
            continue

        # Score = number of keywords found in slug
        score = sum(1 for kw in keywords if kw in slug)
        if score > best_score:
            best_score = score
            best_id = evt["id"]

    if best_id:
        logger.info(
            "Auto-matched '%s' %s → TickPick ID %s (score %d)",
            event_name, evt_date, best_id, best_score,
        )
    else:
        logger.debug("No TickPick match for '%s' on %s", event_name, evt_date)

    return best_id
