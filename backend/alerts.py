"""Price alert system — sends email when a tracked event's price drops below the user's threshold."""
import logging
import smtplib
import datetime
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from backend.db import Event, PriceSnapshot, UserEventAlert

logger = logging.getLogger(__name__)

RETRIGGER_DROP_PCT = 0.10  # Re-alert only if price drops another 10% from last alert price


def _get_latest_tickpick_price(event: Event, quantity: int = 1) -> float | None:
    snaps = sorted(
        [s for s in event.snapshots if s.source == 'tickpick' and (s.quantity or 1) == quantity],
        key=lambda s: s.fetched_at,
    )
    if snaps:
        return snaps[-1].lowest_price
    # Fallback to any snapshot
    all_snaps = sorted(event.snapshots, key=lambda s: s.fetched_at)
    return all_snaps[-1].lowest_price if all_snaps else None


def _send_email(to: str, subject: str, body: str):
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_app_password:
        logger.warning("Email not configured — set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to
    msg.attach(MIMEText(body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, to, msg.as_string())
    logger.info("Alert email sent to %s: %s", to, subject)


def check_and_send_alerts(db: Session):
    """Check all user price alerts and send emails where thresholds are met."""
    alerts = db.query(UserEventAlert).all()
    if not alerts:
        return

    # Load events once
    event_ids = list({a.event_id for a in alerts})
    events_by_id: dict[int, Event] = {
        e.id: e for e in db.query(Event).filter(Event.id.in_(event_ids)).all()
    }

    for alert in alerts:
        event = events_by_id.get(alert.event_id)
        if not event:
            continue

        price = _get_latest_tickpick_price(event)
        if price is None or price >= alert.threshold_price:
            continue

        # Decide whether to (re-)alert
        if alert.last_alert_price is not None:
            # Only re-alert if price dropped another 10%+ since last alert
            if price > alert.last_alert_price * (1 - RETRIGGER_DROP_PCT):
                continue

        date_str = event.event_date.strftime("%B %d, %Y") if event.event_date else "TBD"
        subject = f"Price alert — {event.name} is now ${price:.0f}"
        body = f"""
        <html><body style="font-family:sans-serif;background:#0f0f1a;color:#e0e0f0;padding:24px;">
          <h2 style="color:#a78bfa;">Ticket price alert</h2>
          <table style="border-collapse:collapse;width:100%;max-width:480px;">
            <tr><td style="padding:8px 0;color:#888;">Event</td>
                <td style="padding:8px 0;font-weight:bold;">{event.name}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">Date</td>
                <td style="padding:8px 0;">{date_str}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">Venue</td>
                <td style="padding:8px 0;">{event.venue or 'TBD'}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">City</td>
                <td style="padding:8px 0;">{event.city or 'TBD'}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">Current price</td>
                <td style="padding:8px 0;font-size:24px;font-weight:bold;color:#34d399;">${price:.0f}</td></tr>
            <tr><td style="padding:8px 0;color:#888;">Your threshold</td>
                <td style="padding:8px 0;color:#a78bfa;">${alert.threshold_price:.0f}</td></tr>
          </table>
          <p style="color:#888;font-size:12px;margin-top:24px;">
            You set this alert on Ticket Tracker. Reply to this email to unsubscribe.
          </p>
        </body></html>
        """

        try:
            _send_email(alert.email, subject, body)
            alert.last_alerted_at = datetime.datetime.utcnow()
            alert.last_alert_price = price
            db.commit()
        except Exception as e:
            logger.error("Failed to send alert for event %s to %s: %s", event.id, alert.email, e)
