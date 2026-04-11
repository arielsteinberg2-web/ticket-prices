import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, create_engine, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()
_SessionFactory = None


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    ticketmaster_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # world_cup | concerts | sports
    event_date = Column(DateTime, nullable=True)
    venue = Column(String, nullable=True)
    city = Column(String, nullable=True)
    snapshots = relationship("PriceSnapshot", back_populates="event", lazy="dynamic")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    fetched_at = Column(DateTime, default=func.now())
    lowest_price = Column(Float, nullable=False)
    event = relationship("Event", back_populates="snapshots")


def init_db(engine=None):
    global _SessionFactory
    if engine is None:
        from backend.config import DB_PATH
        engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
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
