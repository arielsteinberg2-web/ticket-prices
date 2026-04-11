import datetime
import pytest
from backend.db import Event, PriceSnapshot


def test_create_event(db_session):
    event = Event(
        ticketmaster_id="tm_001",
        name="USA vs Mexico",
        category="world_cup",
        event_date=datetime.datetime(2026, 6, 22, 20, 0),
        venue="MetLife Stadium",
        city="East Rutherford, NJ",
    )
    db_session.add(event)
    db_session.commit()
    found = db_session.query(Event).filter_by(ticketmaster_id="tm_001").first()
    assert found.name == "USA vs Mexico"
    assert found.category == "world_cup"


def test_create_price_snapshot(db_session):
    event = Event(ticketmaster_id="tm_002", name="Final", category="world_cup")
    db_session.add(event)
    db_session.commit()
    snap = PriceSnapshot(
        event_id=event.id,
        fetched_at=datetime.datetime(2026, 4, 1, 9, 0),
        lowest_price=250.0,
    )
    db_session.add(snap)
    db_session.commit()
    found = db_session.query(PriceSnapshot).filter_by(event_id=event.id).first()
    assert found.lowest_price == 250.0


def test_event_snapshots_relationship(db_session):
    event = Event(ticketmaster_id="tm_003", name="Semifinal", category="world_cup")
    db_session.add(event)
    db_session.commit()
    for price in [300.0, 290.0, 280.0]:
        db_session.add(PriceSnapshot(event_id=event.id, lowest_price=price))
    db_session.commit()
    snapshots = list(event.snapshots)
    assert len(snapshots) == 3


def test_duplicate_ticketmaster_id_raises(db_session):
    from sqlalchemy.exc import IntegrityError
    db_session.add(Event(ticketmaster_id="tm_dup", name="Game A", category="world_cup"))
    db_session.commit()
    db_session.add(Event(ticketmaster_id="tm_dup", name="Game B", category="world_cup"))
    with pytest.raises(IntegrityError):
        db_session.commit()
