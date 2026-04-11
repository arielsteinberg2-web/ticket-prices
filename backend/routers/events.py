import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.db import Event, PriceSnapshot, get_session
from backend.prediction import predict

router = APIRouter(prefix="/api")


@router.get("/events")
def list_events(category: str = None, db: Session = Depends(get_session)):
    query = db.query(Event)
    if category:
        query = query.filter(Event.category == category)
    events = query.all()

    result = []
    for event in events:
        snapshots = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
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
        })
    return result


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

    result = predict(prices, event_date=event_date)
    if result is None:
        return {"has_data": False, "message": "Not enough data yet (need at least 3 days)"}

    return {
        "has_data": True,
        "trend": result.trend,
        "predicted_price_7d": result.predicted_price_7d,
        "recommendation": result.recommendation,
        "slope": result.slope,
    }


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

    classification = "Sports" if category in ("sports", "world_cup") else "Music"
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

    event = Event(
        ticketmaster_id=body.ticketmaster_id,
        name=body.name,
        category=body.category,
        event_date=event_date,
        venue=body.venue,
        city=body.city,
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "id": event.id}
