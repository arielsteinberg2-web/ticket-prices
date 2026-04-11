import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, Event, PriceSnapshot, get_session, init_db
from backend.main import app


@pytest.fixture(autouse=True)
def override_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    init_db(engine)
    Session = sessionmaker(bind=engine)

    def _get_session():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_db(tmp_path, override_db):
    from backend.db import _SessionFactory
    session = _SessionFactory()

    e1 = Event(ticketmaster_id="t1", name="USA vs Mexico", category="world_cup",
               event_date=datetime.datetime(2026, 6, 22))
    e2 = Event(ticketmaster_id="t2", name="Taylor Swift", category="concerts",
               event_date=datetime.datetime(2026, 8, 1))
    session.add_all([e1, e2])
    session.commit()

    for i, price in enumerate([250.0, 240.0, 230.0]):
        session.add(PriceSnapshot(event_id=e1.id, lowest_price=price,
                                  fetched_at=datetime.datetime(2026, 4, i + 1)))
    session.commit()

    result = {"e1_id": e1.id, "e2_id": e2.id}
    session.close()
    return result


def test_list_all_events(client, seeded_db):
    resp = client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_filter_by_category(client, seeded_db):
    resp = client.get("/api/events?category=world_cup")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "USA vs Mexico"


def test_event_has_latest_price(client, seeded_db):
    resp = client.get("/api/events?category=world_cup")
    data = resp.json()
    assert data[0]["latest_price"] == 230.0


def test_get_price_history(client, seeded_db):
    e1_id = seeded_db["e1_id"]
    resp = client.get(f"/api/events/{e1_id}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["lowest_price"] == 250.0


def test_get_prediction(client, seeded_db):
    e1_id = seeded_db["e1_id"]
    resp = client.get(f"/api/events/{e1_id}/prediction")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_data"] is True
    assert data["trend"] in ("rising", "falling", "flat")
    assert data["recommendation"] in ("BUY NOW", "BUY SOON", "WAIT")


def test_get_prediction_insufficient_data(client, seeded_db):
    e2_id = seeded_db["e2_id"]
    resp = client.get(f"/api/events/{e2_id}/prediction")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_data"] is False


def test_event_not_found(client, seeded_db):
    resp = client.get("/api/events/9999/history")
    assert resp.status_code == 404


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
