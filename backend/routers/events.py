import datetime
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy import not_, nullslast
from sqlalchemy.orm import Session, subqueryload
from pydantic import BaseModel
from typing import Optional
from backend.db import Event, PriceSnapshot, UserEvent, get_session
from backend.prediction import predict
from backend.ai_prediction import ai_predict

router = APIRouter(prefix="/api")

# In-memory cache for world_cup list (same for all users, expensive to compute)
_WC_CACHE: tuple[float, list] | None = None  # (timestamp, result)
_WC_CACHE_TTL = 300  # 5 minutes


def _build_events_result(events: list, snaps_by_event: dict, ue_by_event_id: dict) -> list:
    """Compute the API response list from pre-loaded events and snapshots."""
    # Deduplicate events by (name, date) — keep the one with more recent snapshots
    seen_events: dict[tuple, Event] = {}
    for event in events:
        date_key = event.event_date.date().isoformat() if event.event_date else ""
        key = (event.name.lower(), date_key)
        cur_snaps = snaps_by_event.get(event.id, [])
        existing = seen_events.get(key)
        if existing is None or len(cur_snaps) > len(snaps_by_event.get(existing.id, [])):
            seen_events[key] = event
    events = sorted(seen_events.values(), key=lambda e: e.event_date or datetime.datetime.max)

    result = []
    for event in events:
        ue = ue_by_event_id.get(event.id)
        qty = (ue.quantity if ue else None) or event.quantity or 1
        all_snaps = snaps_by_event.get(event.id, [])

        prices_by_qty: dict[int, float] = {}
        for q in range(1, 7):
            q_snaps = [s for s in all_snaps if (s.quantity or 1) == q]
            if q_snaps:
                prices_by_qty[q] = q_snaps[-1].lowest_price

        qty_snaps = [s for s in all_snaps if (s.quantity or 1) == qty] or all_snaps

        # Reject anomalous drop (>70% below previous snapshot)
        if len(qty_snaps) >= 2:
            last, prev = qty_snaps[-1].lowest_price, qty_snaps[-2].lowest_price
            if prev and last < prev * 0.30:
                qty_snaps = qty_snaps[:-1]

        latest_price = prices_by_qty.get(qty) or (qty_snaps[-1].lowest_price if qty_snaps else None)
        if qty in prices_by_qty:
            raw_qty_snaps = [s for s in all_snaps if (s.quantity or 1) == qty]
            if len(raw_qty_snaps) >= 2:
                last, prev = raw_qty_snaps[-1].lowest_price, raw_qty_snaps[-2].lowest_price
                if prev and last < prev * 0.30:
                    prices_by_qty[qty] = prev
                    latest_price = prev

        # Weekly change: compare to snapshot ~7 days ago
        week_ago_snap = None
        if qty_snaps:
            target = qty_snaps[-1].fetched_at - datetime.timedelta(days=7)
            week_ago_snap = min(qty_snaps, key=lambda s: abs((s.fetched_at - target).total_seconds()))
            if week_ago_snap == qty_snaps[-1]:
                week_ago_snap = qty_snaps[0]

        weekly_change = None
        if latest_price and week_ago_snap and week_ago_snap.lowest_price and week_ago_snap != qty_snaps[-1]:
            weekly_change = round(
                (latest_price - week_ago_snap.lowest_price) / week_ago_snap.lowest_price * 100, 1
            )

        result.append({
            "id": event.id,
            "name": event.name,
            "category": event.category,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "venue": event.venue,
            "city": event.city,
            "quantity": qty,
            "latest_price": latest_price,
            "weekly_change_pct": weekly_change,
            "snapshot_count": len(qty_snaps),
            "price_source": qty_snaps[-1].source if qty_snaps else None,
            "price_history": [
                {"fetched_at": s.fetched_at.isoformat(), "lowest_price": s.lowest_price}
                for s in qty_snaps[-20:]
            ],
            "prices_by_qty": prices_by_qty,
        })
    return result


def _load_recent_snaps(db: Session, event_ids: list[int]) -> dict[int, list]:
    """Load last 30 days of snapshots for the given event IDs, grouped by event_id."""
    if not event_ids:
        return {}
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    rows = db.query(PriceSnapshot).filter(
        PriceSnapshot.event_id.in_(event_ids),
        PriceSnapshot.fetched_at >= cutoff,
    ).order_by(PriceSnapshot.event_id, PriceSnapshot.fetched_at.asc()).all()
    by_event: dict[int, list] = {}
    for s in rows:
        by_event.setdefault(s.event_id, []).append(s)
    return by_event


@router.get("/events")
def list_events(category: str = None, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    global _WC_CACHE
    today = datetime.date.today()

    WC_HOST_CITIES = {
        'new york', 'new jersey', 'east rutherford', 'los angeles', 'inglewood',
        'dallas', 'arlington', 'san francisco', 'santa clara', 'seattle',
        'miami', 'miami gardens', 'boston', 'foxborough', 'kansas city',
        'philadelphia', 'houston', 'atlanta', 'toronto', 'vancouver',
        'guadalajara', 'zapopan', 'mexico city', 'monterrey',
    }

    # World Cup — same for everyone, cache the result
    if category == 'world_cup':
        if _WC_CACHE and time.time() - _WC_CACHE[0] < _WC_CACHE_TTL:
            return _WC_CACHE[1]

        events = db.query(Event).filter(
            Event.name.ilike('%World Cup%'),
            not_(Event.name.ilike('%FEI%')),
            not_(Event.name.ilike('%Pacific%')),
            (Event.event_date == None) | (Event.event_date >= datetime.datetime.combine(today, datetime.time.min)),
        ).order_by(nullslast(Event.event_date.asc())).all()

        events = [
            e for e in events
            if e.city is None or any(h in e.city.lower() for h in WC_HOST_CITIES)
        ]
        event_ids = [e.id for e in events]
        snaps_by_event = _load_recent_snaps(db, event_ids)
        result = _build_events_result(events, snaps_by_event, {})
        _WC_CACHE = (time.time(), result)
        return result

    # User events — per-user, no cache
    if not x_user_id:
        return []
    ue_rows = db.query(UserEvent).filter(UserEvent.user_id == x_user_id).all()
    if not ue_rows:
        return []
    ue_by_event_id = {ue.event_id: ue for ue in ue_rows}

    events = db.query(Event).filter(
        Event.id.in_(list(ue_by_event_id.keys())),
        not_(Event.name.ilike('%World Cup%')),
        not_(Event.name.ilike('%FIFA%')),
        (Event.event_date == None) | (Event.event_date >= datetime.datetime.combine(today, datetime.time.min)),
    ).order_by(nullslast(Event.event_date.asc())).all()
    if category:
        events = [e for e in events if e.category == category]

    event_ids = [e.id for e in events]
    snaps_by_event = _load_recent_snaps(db, event_ids)
    return _build_events_result(events, snaps_by_event, ue_by_event_id)


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    ue = db.query(UserEvent).filter_by(event_id=event_id, user_id=x_user_id).first()
    if not ue:
        raise HTTPException(status_code=404, detail="Event not tracked by this user")
    db.delete(ue)
    db.commit()
    return {"status": "ok"}


@router.get("/events/{event_id}/history")
def get_history(event_id: int, quantity: int = None, db: Session = Depends(get_session)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    qty = quantity or event.quantity or 1
    all_snaps = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
    snapshots = [s for s in all_snaps if (s.quantity or 1) == qty] or all_snaps
    return [
        {"fetched_at": s.fetched_at.isoformat(), "lowest_price": s.lowest_price}
        for s in snapshots
    ]


@router.get("/events/{event_id}/prediction")
def get_prediction(event_id: int, quantity: int = None, db: Session = Depends(get_session)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    qty = quantity or event.quantity or 1
    all_snaps = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
    snapshots = [s for s in all_snaps if (s.quantity or 1) == qty] or all_snaps
    prices = [(s.fetched_at.date(), s.lowest_price) for s in snapshots]
    event_date = event.event_date.date() if event.event_date else None

    result = ai_predict(prices, event_name=event.name, event_date=event_date)
    if result is None:
        return {"has_data": False, "message": "Not enough data yet (need at least 7 days)"}

    return {
        "has_data": True,
        "trend": result.trend,
        "predicted_price_7d": result.predicted_price_7d,
        "recommendation": result.recommendation,
        "slope": result.slope,
        "score": result.score,
        "confidence": result.confidence,
    }


@router.get("/status")
def get_status():
    """Return token expiry and system health info."""
    import base64, json as _json, datetime as _dt
    from backend.config import TICKPICK_TOKEN

    token_info = {"configured": bool(TICKPICK_TOKEN), "expires_at": None, "days_remaining": None, "valid": False}

    if TICKPICK_TOKEN:
        try:
            payload_b64 = TICKPICK_TOKEN.split('.')[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            exp = payload.get('exp')
            if exp:
                exp_dt = _dt.datetime.utcfromtimestamp(exp)
                days_left = (exp_dt - _dt.datetime.utcnow()).days
                token_info.update({
                    "expires_at": exp_dt.isoformat(),
                    "days_remaining": days_left,
                    "valid": days_left > 0,
                })
        except Exception:
            pass

    return {"tickpick_token": token_info}


class QuantityRequest(BaseModel):
    category: str
    quantity: int


@router.post("/quantity")
def set_category_quantity(body: QuantityRequest, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    """Set ticket quantity for all of this user's events in a category."""
    if not (1 <= body.quantity <= 6):
        raise HTTPException(status_code=400, detail="Quantity must be 1-6")
    if not x_user_id:
        return {"status": "ok", "updated": 0}
    # Get the user's event IDs for this category
    event_ids = [e.id for e in db.query(Event).filter(Event.category == body.category).all()]
    ues = db.query(UserEvent).filter(
        UserEvent.user_id == x_user_id,
        UserEvent.event_id.in_(event_ids),
    ).all()
    for ue in ues:
        ue.quantity = body.quantity
    db.commit()
    return {"status": "ok", "updated": len(ues)}


@router.post("/fetch")
def trigger_fetch(db: Session = Depends(get_session)):
    """Manually trigger a price fetch for all watchlist targets."""
    from backend.scheduler import run_fetch_job
    run_fetch_job(db, force=True)
    return {"status": "ok", "message": "Fetch triggered"}


@router.get("/search")
def search_events(q: str, category: str = "events", db: Session = Depends(get_session), x_user_id: str = Header(None)):
    """Search events. Uses TickPick sitemap cache (instant) first; falls back to Ticketmaster live search."""
    from backend.tickpick_fetcher import search_sitemap_by_keyword

    WC_KEYWORDS = ('world cup', 'fifa', 'coupe du monde')

    # --- Fast path: TickPick sitemap cache (in-memory, no network) ---
    sitemap_hits = search_sitemap_by_keyword(q, limit=100)

    if category == 'events':
        sitemap_hits = [r for r in sitemap_hits if not any(kw in r['name'].lower() for kw in WC_KEYWORDS)]

    if sitemap_hits:
        # Batch-load any existing DB events by tickpick_id
        tp_ids = [r['tickpick_id'] for r in sitemap_hits]
        existing_by_tpid: dict[str, Event] = {
            e.tickpick_id: e
            for e in db.query(Event).options(subqueryload(Event.snapshots)).filter(
                Event.tickpick_id.in_(tp_ids)
            ).all()
            if e.tickpick_id
        }
        # User's tracked event IDs
        user_event_ids: set[int] = set()
        if x_user_id:
            user_event_ids = {ue.event_id for ue in db.query(UserEvent).filter(UserEvent.user_id == x_user_id).all()}

        results = []
        seen: set[tuple] = set()
        for r in sitemap_hits:
            key = (r['event_date'][:10], r['name'].lower()[:30])
            if key in seen:
                continue
            seen.add(key)

            existing = existing_by_tpid.get(r['tickpick_id'])
            price = None
            if existing:
                snaps = sorted(
                    [s for s in existing.snapshots if s.source == 'tickpick' and (s.quantity or 1) == 1],
                    key=lambda s: s.fetched_at,
                )
                if snaps:
                    price = snaps[-1].lowest_price

            results.append({
                "ticketmaster_id": r['ticketmaster_id'],
                "name": r['name'],
                "category": category,
                "event_date": r['event_date'],
                "venue": r['venue'],
                "city": r['city'],
                "lowest_price": price,
                "already_tracked": existing is not None and existing.id in user_event_ids,
                "event_id": existing.id if existing else None,
            })
        return results

    # --- Slow fallback: Ticketmaster live API ---
    from backend.fetcher import fetch_events, build_event_record
    from backend.config import TICKETMASTER_API_KEY

    if category == "world_cup":
        classification = "Sports"
    elif category == "events":
        classification = None
    else:
        classification = "Sports"
    try:
        raw_events = fetch_events(q, classification, TICKETMASTER_API_KEY)
    except Exception:
        return []

    tracked_by_tmid: dict[str, Event] = {
        e.ticketmaster_id: e
        for e in db.query(Event).options(subqueryload(Event.snapshots)).filter(
            Event.ticketmaster_id.isnot(None)
        ).all()
        if e.ticketmaster_id
    }
    user_event_ids_tm: set[int] = set()
    if x_user_id:
        user_event_ids_tm = {ue.event_id for ue in db.query(UserEvent).filter(UserEvent.user_id == x_user_id).all()}

    results = []
    for raw in raw_events[:100]:
        record = build_event_record(raw, category)
        if category == 'events':
            if any(kw in record["name"].lower() for kw in WC_KEYWORDS):
                continue
        existing = tracked_by_tmid.get(record["ticketmaster_id"])
        price = record["lowest_price"]
        if existing:
            all_snaps = sorted(existing.snapshots, key=lambda s: s.fetched_at)
            qty = existing.quantity or 1
            qty_snaps = [s for s in all_snaps if (s.quantity or 1) == qty] or all_snaps
            if qty_snaps:
                price = qty_snaps[-1].lowest_price
        results.append({
            "ticketmaster_id": record["ticketmaster_id"],
            "name": record["name"],
            "category": category,
            "event_date": record["event_date"].isoformat() if record["event_date"] else None,
            "venue": record["venue"],
            "city": record["city"],
            "lowest_price": price,
            "already_tracked": existing is not None and existing.id in user_event_ids_tm,
            "event_id": existing.id if existing else None,
        })

    seen2: set[tuple] = set()
    deduped = []
    for r in results:
        key = (r["event_date"], (r["venue"] or "").lower())
        if key not in seen2:
            seen2.add(key)
            deduped.append(r)
    deduped.sort(key=lambda r: r["event_date"] or "")
    return deduped


class TrackRequest(BaseModel):
    ticketmaster_id: str
    name: str
    category: str
    event_date: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    lowest_price: Optional[float] = None
    tickpick_url: Optional[str] = None


def _discover_tickpick_in_background(event_id: int, event_name: str, event_date: datetime.datetime):
    """Run in background after track: find TickPick ID and fetch prices for all quantities."""
    import logging
    from backend.db import _SessionFactory
    from backend.config import TICKPICK_TOKEN
    from backend.tickpick_fetcher import find_tickpick_id, fetch_tickpick_prices_all_qty
    logger = logging.getLogger(__name__)
    if not _SessionFactory or not TICKPICK_TOKEN:
        return
    db = _SessionFactory()
    try:
        tp_id = find_tickpick_id(event_name, event_date)
        if not tp_id:
            return
        event = db.query(Event).filter_by(id=event_id).first()
        if not event:
            return
        event.tickpick_id = tp_id
        now = datetime.datetime.utcnow()
        prices_by_qty = fetch_tickpick_prices_all_qty(tp_id, TICKPICK_TOKEN)
        for qty, price in prices_by_qty.items():
            db.add(PriceSnapshot(
                event_id=event_id,
                fetched_at=now,
                lowest_price=price,
                source="tickpick",
                quantity=qty,
            ))
        db.commit()
        logger.info("Background: TickPick ID %s, prices %s for '%s'", tp_id, prices_by_qty, event_name)
    except Exception as e:
        logger.error("Background TickPick discovery failed for event %s: %s", event_id, e)
        db.rollback()
    finally:
        db.close()


@router.post("/track")
def track_event(body: TrackRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    """Add an event to the tracking list. Returns immediately; TickPick discovery runs in background."""
    # Find or create the shared Event row
    event = db.query(Event).filter_by(ticketmaster_id=body.ticketmaster_id).first()

    if event is None:
        event_date = None
        if body.event_date:
            try:
                event_date = datetime.datetime.fromisoformat(body.event_date.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                pass
        event = Event(
            ticketmaster_id=body.ticketmaster_id,
            name=body.name,
            category=body.category,
            event_date=event_date,
            venue=body.venue,
            city=body.city,
        )
        db.add(event)
        db.flush()

        now = datetime.datetime.utcnow()
        price_saved = False

        # Save price from search result immediately
        tm_price = body.lowest_price
        if tm_price is not None:
            db.add(PriceSnapshot(event_id=event.id, fetched_at=now, lowest_price=tm_price, source="ticketmaster"))
            price_saved = True

        # Fall back to SeatGeek if no price
        if not price_saved:
            from backend.config import SEATGEEK_CLIENT_ID
            from backend.seatgeek_fetcher import fetch_seatgeek_events, build_seatgeek_record
            if SEATGEEK_CLIENT_ID:
                try:
                    for raw in fetch_seatgeek_events(body.name, SEATGEEK_CLIENT_ID)[:10]:
                        record = build_seatgeek_record(raw, body.category)
                        if record["lowest_price"] is None:
                            continue
                        sg_words = set(record["name"].lower().split())
                        body_words = set(body.name.lower().split())
                        if len(sg_words & body_words) / max(len(body_words), 1) > 0.4:
                            event.seatgeek_id = record["seatgeek_id"]
                            db.add(PriceSnapshot(event_id=event.id, fetched_at=now, lowest_price=record["lowest_price"], source="seatgeek"))
                            price_saved = True
                            break
                except Exception:
                    pass
    else:
        price_saved = bool(event.snapshots)

    # Check if user is already tracking this event
    existing_ue = db.query(UserEvent).filter_by(event_id=event.id, user_id=x_user_id).first() if x_user_id else None
    if existing_ue:
        db.commit()
        return {"status": "already_tracked", "id": event.id}

    # Create UserEvent link
    if x_user_id:
        db.add(UserEvent(user_id=x_user_id, event_id=event.id, quantity=1))

    db.commit()

    # Discover TickPick ID in background (slow sitemap crawl — don't block the response)
    event_date_val = event.event_date
    if event_date_val and not event.tickpick_id:
        background_tasks.add_task(_discover_tickpick_in_background, event.id, body.name, event_date_val)

    return {"status": "ok", "id": event.id, "price_fetched": price_saved}
