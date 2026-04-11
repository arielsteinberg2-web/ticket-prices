import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
