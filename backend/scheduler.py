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

                # Upsert event (always, so SeatGeek/TickPick can fill in prices later)
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

                # Store price snapshot only if TM has a price
                if record["lowest_price"] is not None:
                    snapshot = PriceSnapshot(
                        event_id=event.id,
                        fetched_at=now,
                        lowest_price=record["lowest_price"],
                        source="ticketmaster",
                    )
                    db.add(snapshot)

        # Supplemental SeatGeek fetch for events with no price
        from backend.config import SEATGEEK_CLIENT_ID
        from backend.seatgeek_fetcher import fetch_seatgeek_events, build_seatgeek_record

        if SEATGEEK_CLIENT_ID:
            for target in targets:
                logger.info("SeatGeek fetch: %s", target["keyword"])
                sg_events = fetch_seatgeek_events(target["keyword"], SEATGEEK_CLIENT_ID)

                for raw in sg_events:
                    record = build_seatgeek_record(raw, category=target["category"])
                    if record["lowest_price"] is None:
                        continue

                    # Try to match to existing event by seatgeek_id first
                    event = db.query(Event).filter_by(seatgeek_id=record["seatgeek_id"]).first()

                    # If no match by seatgeek_id, try matching by date + name similarity
                    if event is None and record["event_date"]:
                        from datetime import timedelta
                        candidates = db.query(Event).filter(
                            Event.category == record["category"],
                            Event.event_date >= record["event_date"] - timedelta(days=1),
                            Event.event_date <= record["event_date"] + timedelta(days=1),
                        ).all()
                        for c in candidates:
                            # Simple word overlap check
                            sg_words = set(record["name"].lower().split())
                            db_words = set(c.name.lower().split())
                            if len(sg_words & db_words) / max(len(sg_words), 1) > 0.4:
                                event = c
                                break

                    # If still no match, create new event
                    if event is None:
                        event = Event(
                            ticketmaster_id=f"sg_{record['seatgeek_id']}",
                            seatgeek_id=record["seatgeek_id"],
                            name=record["name"],
                            category=record["category"],
                            event_date=record["event_date"],
                            venue=record["venue"],
                            city=record["city"],
                        )
                        db.add(event)
                        db.flush()
                    elif event.seatgeek_id is None:
                        event.seatgeek_id = record["seatgeek_id"]

                    db.add(PriceSnapshot(
                        event_id=event.id,
                        fetched_at=now,
                        lowest_price=record["lowest_price"],
                        source="seatgeek",
                    ))

        # TickPick: auto-discover IDs for events that don't have one yet
        from backend.config import TICKPICK_TOKEN
        from backend.tickpick_fetcher import fetch_tickpick_price, find_tickpick_id, _get_sitemap_events
        if TICKPICK_TOKEN:
            # Warm the sitemap cache (downloads only if stale/missing)
            _get_sitemap_events()
            events_without_tp = db.query(Event).filter(
                Event.tickpick_id.is_(None),
                Event.event_date.isnot(None),
            ).all()
            for event in events_without_tp:
                tp_id = find_tickpick_id(event.name, event.event_date)
                if tp_id:
                    event.tickpick_id = tp_id
                    logger.info("Auto-assigned TickPick ID %s to '%s'", tp_id, event.name)

        # TickPick price refresh for events with a tickpick_id
        if TICKPICK_TOKEN:
            tp_events = db.query(Event).filter(Event.tickpick_id.isnot(None)).all()
            for event in tp_events:
                price = fetch_tickpick_price(event.tickpick_id, TICKPICK_TOKEN)
                if price is not None:
                    db.add(PriceSnapshot(
                        event_id=event.id,
                        fetched_at=now,
                        lowest_price=price,
                        source="tickpick",
                    ))
                    logger.info("TickPick price for %s: $%.0f", event.name, price)

        db.commit()
        logger.info("Fetch job complete at %s", now.isoformat())

        # Check price alerts after every fetch
        from backend.alerts import check_and_send_alerts
        check_and_send_alerts(db)

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
        trigger="interval",
        hours=4,
        id="price_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — price fetch every 4 hours")
    return scheduler
