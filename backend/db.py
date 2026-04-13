import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, create_engine, func, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()
_SessionFactory = None


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    ticketmaster_id = Column(String, unique=True, nullable=False)
    seatgeek_id = Column(String, nullable=True, unique=True)
    tickpick_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # world_cup | concerts | sports
    event_date = Column(DateTime, nullable=True)
    venue = Column(String, nullable=True)
    city = Column(String, nullable=True)
    snapshots = relationship("PriceSnapshot", back_populates="event", lazy="select")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    fetched_at = Column(DateTime, default=func.now())
    lowest_price = Column(Float, nullable=False)
    source = Column(String, nullable=True, default="ticketmaster")
    event = relationship("Event", back_populates="snapshots")


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    alerted_at = Column(DateTime, default=func.now())
    price_at_alert = Column(Float, nullable=False)


def init_db(engine=None):
    global _SessionFactory
    if engine is None:
        from backend.config import DB_PATH, DATABASE_URL
        if DATABASE_URL:
            engine = create_engine(DATABASE_URL)
        else:
            engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    # Add source column if it doesn't exist (migration for existing DBs)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE price_snapshots ADD COLUMN source VARCHAR"))
            conn.commit()
    except Exception:
        pass  # Column already exists

    # Add seatgeek_id column if it doesn't exist (migration for existing DBs)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE events ADD COLUMN seatgeek_id VARCHAR"))
            conn.commit()
    except Exception:
        pass  # Column already exists

    # Add tickpick_id column if it doesn't exist
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE events ADD COLUMN tickpick_id VARCHAR"))
            conn.commit()
    except Exception:
        pass  # Column already exists

    # Add price_alerts table if it doesn't exist (handled by create_all above for new DBs)
    # For existing DBs, create_all is idempotent — it only creates missing tables

    _SessionFactory = sessionmaker(bind=engine)
    return engine


def get_session() -> Session:
    if _SessionFactory is None:
        raise RuntimeError("DB not initialized. Call init_db() first.")
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()
