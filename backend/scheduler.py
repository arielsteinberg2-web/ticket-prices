import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from backend.config import TICKETMASTER_API_KEY, load_watchlist, get_search_targets
from backend.fetcher import fetch_events, build_event_record
from backend.db import Event, PriceSnapshot

logger = logging.getLogger(__name__)


def run_fetch_job(db: Session = None):
    """
    Fetch latest lowest prices for all watchlist targets and upsert into DB.
    If db is None, creates its own session from the global _SessionFactory.
    """
    from backend.db import _SessionFactory
    own_session = db is None
    if own_session:
        if _SessionFactory is None:
            logger.error("DB not initialized. Call init_db() before running fetch job.")
            return
        db = _SessionFactory()

    try:
        watchlist = load_watchlist()
        targets = get_search_targets(watchlist)
        now = datetime.datetime.utcnow()

        for target in targets:
            logger.info("Fetching: %s (%s)", target["keyword"], target["category"])
            raw_events = fetch_events(target["keyword"], target["classification"], TICKETMASTER_API_KEY)

            for raw in raw_events:
                record = build_event_record(raw, category=target["category"])
                if record["lowest_price"] is None:
                    continue  # skip events with no price listed

                # Upsert event
                event = db.query(Event).filter_by(ticketmaster_id=record["ticketmaster_id"]).first()
                if event is None:
                    event = Event(
                        ticketmaster_id=record["ticketmaster_id"],
                        name=record["name"],
                        category=record["category"],
                        event_date=record["event_date"],
                        venue=record["venue"],
                        city=record["city"],
                    )
                    db.add(event)
                    db.flush()

                # Store price snapshot
                snapshot = PriceSnapshot(
                    event_id=event.id,
                    fetched_at=now,
                    lowest_price=record["lowest_price"],
                )
                db.add(snapshot)

        db.commit()
        logger.info("Fetch job complete at %s", now.isoformat())

    except Exception as e:
        logger.error("Fetch job failed: %s", e)
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


def start_scheduler() -> BackgroundScheduler:
    """Start APScheduler to run run_fetch_job daily at 09:00 local time."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_fetch_job,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_price_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily fetch at 09:00")
    return scheduler
