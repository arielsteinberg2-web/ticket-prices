import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import not_
from sqlalchemy.orm import Session, subqueryload
from pydantic import BaseModel
from typing import Optional
from backend.db import Event, PriceSnapshot, get_session
from backend.prediction import predict
from backend.ai_prediction import ai_predict

router = APIRouter(prefix="/api")


@router.get("/events")
def list_events(category: str = None, db: Session = Depends(get_session)):
    # Load events + all snapshots in 2 queries instead of N+1
    query = db.query(Event).options(subqueryload(Event.snapshots))
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
        events = query.all()

    result = []
    for event in events:
        snapshots = sorted(event.snapshots, key=lambda s: s.fetched_at)
        latest_price = snapshots[-1].lowest_price if snapshots else None
        week_ago_snap = snapshots[-8] if len(snapshots) >= 8 else (snapshots[0] if snapshots else None)
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
            "latest_price": latest_price,
            "weekly_change_pct": weekly_change,
            "snapshot_count": len(snapshots),
            "price_source": snapshots[-1].source if snapshots else None,
            "price_history": [s.lowest_price for s in snapshots[-20:]],
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
def get_history(event_id: int, db: Session = Depends(get_session)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    snapshots = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
    return [
        {"fetched_at": s.fetched_at.isoformat(), "lowest_price": s.lowest_price}
        for s in snapshots
    ]


@router.get("/events/{event_id}/prediction")
def get_prediction(event_id: int, db: Session = Depends(get_session)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    snapshots = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
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


@router.post("/fetch")
def trigger_fetch(db: Session = Depends(get_session)):
    """Manually trigger a price fetch for all watchlist targets."""
    from backend.scheduler import run_fetch_job
    run_fetch_job(db)
    return {"status": "ok", "message": "Fetch triggered"}


@router.get("/search")
def search_events(q: str, category: str = "sports", db: Session = Depends(get_session)):
    """Search Ticketmaster live for events matching q. Returns top 20 results."""
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
    except Exception as e:
        return []

    results = []
    for raw in raw_events[:20]:
        record = build_event_record(raw, category)
        existing = db.query(Event).filter_by(ticketmaster_id=record["ticketmaster_id"]).first()
        results.append({
            "ticketmaster_id": record["ticketmaster_id"],
            "name": record["name"],
            "category": category,
            "event_date": record["event_date"].isoformat() if record["event_date"] else None,
            "venue": record["venue"],
            "city": record["city"],
            "lowest_price": record["lowest_price"],
            "already_tracked": existing is not None,
        })
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


@router.post("/track")
def track_event(body: TrackRequest, db: Session = Depends(get_session)):
    """Add an event to the tracking list."""
    existing = db.query(Event).filter_by(ticketmaster_id=body.ticketmaster_id).first()
    if existing:
        return {"status": "already_tracked", "id": existing.id}

    event_date = None
    if body.event_date:
        try:
            event_date = datetime.datetime.fromisoformat(body.event_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass

    # Resolve TickPick event ID: from explicit URL, or auto-discover via sitemaps
    tickpick_id = None
    if body.tickpick_url:
        from backend.tickpick_fetcher import extract_tickpick_id
        tickpick_id = extract_tickpick_id(body.tickpick_url)
    elif event_date:
        from backend.tickpick_fetcher import find_tickpick_id
        tickpick_id = find_tickpick_id(body.name, event_date)

    event = Event(
        ticketmaster_id=body.ticketmaster_id,
        name=body.name,
        category=body.category,
        event_date=event_date,
        venue=body.venue,
        city=body.city,
        tickpick_id=tickpick_id,
    )
    db.add(event)
    db.flush()

    now = datetime.datetime.utcnow()
    price_saved = False

    # Try price from search result first, then direct TM lookup
    tm_price = body.lowest_price
    if tm_price is None:
        from backend.fetcher import fetch_event_price
        from backend.config import TICKETMASTER_API_KEY
        tm_price = fetch_event_price(body.ticketmaster_id, TICKETMASTER_API_KEY)

    if tm_price is not None:
        db.add(PriceSnapshot(
            event_id=event.id,
            fetched_at=now,
            lowest_price=tm_price,
            source="ticketmaster",
        ))
        price_saved = True

    # Fall back to SeatGeek if no Ticketmaster price
    if not price_saved:
        from backend.config import SEATGEEK_CLIENT_ID
        from backend.seatgeek_fetcher import fetch_seatgeek_events, build_seatgeek_record
        if SEATGEEK_CLIENT_ID:
            try:
                sg_events = fetch_seatgeek_events(body.name, SEATGEEK_CLIENT_ID)
                for raw in sg_events[:10]:
                    record = build_seatgeek_record(raw, body.category)
                    if record["lowest_price"] is None:
                        continue
                    # Match by name similarity
                    sg_words = set(record["name"].lower().split())
                    body_words = set(body.name.lower().split())
                    if len(sg_words & body_words) / max(len(body_words), 1) > 0.4:
                        event.seatgeek_id = record["seatgeek_id"]
                        db.add(PriceSnapshot(
                            event_id=event.id,
                            fetched_at=now,
                            lowest_price=record["lowest_price"],
                            source="seatgeek",
                        ))
                        price_saved = True
                        break
            except Exception:
                pass

    # Try TickPick (URL provided or auto-discovered) if no price yet
    if not price_saved and tickpick_id:
        from backend.config import TICKPICK_TOKEN
        from backend.tickpick_fetcher import fetch_tickpick_price
        if TICKPICK_TOKEN:
            tp_price = fetch_tickpick_price(tickpick_id, TICKPICK_TOKEN)
            if tp_price is not None:
                db.add(PriceSnapshot(
                    event_id=event.id,
                    fetched_at=now,
                    lowest_price=tp_price,
                    source="tickpick",
                ))
                price_saved = True

    db.commit()
    return {"status": "ok", "id": event.id, "price_fetched": price_saved}
