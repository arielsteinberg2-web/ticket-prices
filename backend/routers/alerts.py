import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db import Event, UserEventAlert, get_session

router = APIRouter(prefix="/api")


class AlertRequest(BaseModel):
    event_id: int
    email: str
    threshold_price: float


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_session), x_user_id: str = Header(None)):
    if not x_user_id:
        return {}
    rows = db.query(UserEventAlert).filter(UserEventAlert.user_id == x_user_id).all()
    return {
        r.event_id: {"threshold_price": r.threshold_price, "email": r.email}
        for r in rows
    }


@router.post("/alerts")
def set_alert(body: AlertRequest, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing user id")
    existing = db.query(UserEventAlert).filter_by(user_id=x_user_id, event_id=body.event_id).first()
    if existing:
        existing.email = body.email
        existing.threshold_price = body.threshold_price
        existing.last_alerted_at = None
        existing.last_alert_price = None
    else:
        db.add(UserEventAlert(
            user_id=x_user_id,
            event_id=body.event_id,
            email=body.email,
            threshold_price=body.threshold_price,
        ))
    db.commit()
    return {"status": "ok"}


@router.delete("/alerts/{event_id}")
def delete_alert(event_id: int, db: Session = Depends(get_session), x_user_id: str = Header(None)):
    db.query(UserEventAlert).filter_by(user_id=x_user_id, event_id=event_id).delete()
    db.commit()
    return {"status": "ok"}
