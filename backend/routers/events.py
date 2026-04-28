import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import not_, nullslast
from sqlalchemy.orm import Session, subqueryload
from pydantic import BaseModel
from typing import Optional
from backend.db import Event, PriceSnapshot, get_session
from backend.prediction import predict
from backend.ai_prediction import ai_predict

router = APIRouter(prefix="/api")


@router.get("/events")
def list_events(category: str = None, db: Session = Depends(get_session)):
    # Load events + all snapshots in 2 queries instead of N+1, sorted by date
    query = db.query(Event).options(subqueryload(Event.snapshots)).order_by(nullslast(Event.event_date.asc()))
    if category:
        query = query.filter(Event.category == category)

    WC_HOST_CITIES = {
        'new york', 'new jersey', 'east rutherford', 'los angeles', 'inglewood',
        'dallas', 'arlington', 'san francisco', 'santa clara', 'seattle',
        'miami', 'miami gardens', 'boston', 'foxborough', 'kansas city',
        'philadelphia', 'houston', 'atlanta', 'toronto', 'vancouver',
        'guadalajara', 'zapopan', 'mexico city', 'monterrey',
    }

    if category == 'world_cup':
        query = query.filter(
            Event.name.ilike('%World Cup%'),
            not_(Event.name.ilike('%FEI%')),
            not_(Event.name.ilike('%Pacific%')),
        )
        events = query.all()
        events = [
            e for e in events
            if e.city is None or any(h in e.city.lower() for h in WC_HOST_CITIES)
        ]
    else:
        query = query.filter(
            not_(Event.name.ilike('%World Cup%')),
            not_(Event.name.ilike('%FIFA%')),
        )
        events = query.all()

    result = []
    for event in events:
        qty = event.quantity or 1
        all_snaps = sorted(event.snapshots, key=lambda s: s.fetched_at)

        # Build prices_by_qty: latest price for each quantity (1-6)
        prices_by_qty: dict[int, float] = {}
        for q in range(1, 7):
            q_snaps = [s for s in all_snaps if (s.quantity or 1) == q]
            if q_snaps:
                prices_by_qty[q] = q_snaps[-1].lowest_price

        # Use quantity-matched snapshots for display; fall back to all for old rows
        qty_snaps = [s for s in all_snaps if (s.quantity or 1) == qty] or all_snaps
        latest_price = prices_by_qty.get(qty) or (qty_snaps[-1].lowest_price if qty_snaps else None)

        week_ago_snap = qty_snaps[-8] if len(qty_snaps) >= 8 else (qty_snaps[0] if qty_snaps else None)
        weekly_change = None
        if latest_price and week_ago_snap and week_ago_snap.lowest_price:
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
            "price_history": [s.lowest_price for s in qty_snaps[-20:]],
            "prices_by_qty": prices_by_qty,
        })
    return result


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_session)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.query(PriceSnapshot).filter_by(event_id=event_id).delete()
    db.delete(event)
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
        return {"has_data": False, "message": "Not enough data yet (need at least 3 days)"}

    return {
        "has_data": True,
        "trend": result.trend,
        "predicted_price_7d": result.predicted_price_7d,
        "recommendation": result.recommendation,
        "slope": result.slope,
        "score": result.score,
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
def set_category_quantity(body: QuantityRequest, db: Session = Depends(get_session)):
    """Set ticket quantity for all events in a category. Prices for all quantities are pre-fetched."""
    if not (1 <= body.quantity <= 6):
        raise HTTPException(status_code=400, detail="Quantity must be 1-6")
    events = db.query(Event).filter(Event.category == body.category).all()
    for event in events:
        event.quantity = body.quantity
    db.commit()
    return {"status": "ok", "updated": len(events)}


@router.post("/fetch")
def trigger_fetch(db: Session = Depends(get_session)):
    """Manually trigger a price fetch for all watchlist targets."""
    from backend.scheduler import run_fetch_job
    run_fetch_job(db, force=True)
    return {"status": "ok", "message": "Fetch triggered"}


@router.get("/search")
def search_events(q: str, category: str = "sports", db: Session = Depends(get_session)):
    """Search Ticketmaster live for events matching q. Returns up to 100 results sorted by date."""
    from backend.fetcher import fetch_events, build_event_record
    from backend.config import TICKETMASTER_API_KEY

    if category == "world_cup":
        classification = "Sports"
    elif category == "events":
        classification = None  # search all types
    else:
        classification = "Sports"
    try:
        raw_events = fetch_events(q, classification, TICKETMASTER_API_KEY)
    except Exception:
        return []

    # Pre-load all tracked events with their snapshots in one query
    tracked_by_tmid: dict[str, Event] = {
        e.ticketmaster_id: e
        for e in db.query(Event).options(subqueryload(Event.snapshots)).filter(
            Event.ticketmaster_id.isnot(None)
        ).all()
        if e.ticketmaster_id
    }

    WC_KEYWORDS = ('world cup', 'fifa', 'coupe du monde')

    results = []
    for raw in raw_events[:100]:
        record = build_event_record(raw, category)

        # When browsing events, exclude world cup / FIFA matches
        if category == 'events':
            name_lower = record["name"].lower()
            if any(kw in name_lower for kw in WC_KEYWORDS):
                continue

        existing = tracked_by_tmid.get(record["ticketmaster_id"])

        # For already-tracked events use the stored TickPick/DB price
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
            "already_tracked": existing is not None,
        })

    # Sort by event date ascending
    results.sort(key=lambda r: r["event_date"] or "")
    return results


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
def track_event(body: TrackRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_session)):
    """Add an event to the tracking list. Returns immediately; TickPick discovery runs in background."""
    existing = db.query(Event).filter_by(ticketmaster_id=body.ticketmaster_id).first()
    if existing:
        return {"status": "already_tracked", "id": existing.id}

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

    db.commit()

    # Discover TickPick ID in background (slow sitemap crawl — don't block the response)
    if event_date:
        background_tasks.add_task(_discover_tickpick_in_background, event.id, body.name, event_date)

    return {"status": "ok", "id": event.id, "price_fetched": price_saved}
