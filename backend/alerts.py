"""
Price alert system.
Sends email when Argentina game prices drop below the configured threshold.
"""
import logging
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from backend.db import Event, PriceSnapshot, PriceAlert

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 600       # Send alert when price drops below this
RETRIGGER_DROP_PCT = 0.10   # Re-alert only if price drops another 10% from last alert


def _get_latest_price(event) -> float | None:
    snapshots = sorted(list(event.snapshots), key=lambda s: s.fetched_at)
    if not snapshots:
        return None
    return snapshots[-1].lowest_price


def _send_email(to: str, subject: str, body: str):
    import os
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
    """
    Check all Argentina World Cup events. Send email if:
    - Latest price is below ALERT_THRESHOLD, AND
    - No alert has been sent for this event yet, OR price dropped >=10% from last alert price.
    """
    argentina_events = db.query(Event).filter(
        Event.category == "world_cup",
        Event.name.ilike("%argentina%"),
    ).all()

    for event in argentina_events:
        price = _get_latest_price(event)
        if price is None or price >= ALERT_THRESHOLD:
            continue

        # Check last alert for this event
        last_alert = (
            db.query(PriceAlert)
            .filter_by(event_id=event.id)
            .order_by(PriceAlert.alerted_at.desc())
            .first()
        )

        should_alert = False
        if last_alert is None:
            should_alert = True  # First time below threshold
        elif price <= last_alert.price_at_alert * (1 - RETRIGGER_DROP_PCT):
            should_alert = True  # Price dropped another 10%+ since last alert

        if not should_alert:
            continue

        # Format event date
        date_str = ""
        if event.event_date:
            date_str = event.event_date.strftime("%B %d, %Y")

        subject = f"🇦🇷 Argentina ticket alert — ${price:.0f} ({event.city or event.venue or 'TBD'})"

        body = f"""
        <html><body style="font-family: sans-serif; background: #0f0f1a; color: #e0e0f0; padding: 24px;">
          <h2 style="color: #a78bfa;">Argentina ticket price alert</h2>
          <table style="border-collapse: collapse; width: 100%; max-width: 480px;">
            <tr><td style="padding: 8px 0; color: #888;">Match</td>
                <td style="padding: 8px 0; font-weight: bold;">{event.name}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Date</td>
                <td style="padding: 8px 0;">{date_str}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Venue</td>
                <td style="padding: 8px 0;">{event.venue or "TBD"}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">City</td>
                <td style="padding: 8px 0;">{event.city or "TBD"}</td></tr>
            <tr><td style="padding: 8px 0; color: #888;">Current lowest price</td>
                <td style="padding: 8px 0; font-size: 24px; font-weight: bold; color: #34d399;">${price:.0f}</td></tr>
          </table>
          <p style="color: #888; font-size: 12px; margin-top: 24px;">
            Alert triggered because price dropped below ${ALERT_THRESHOLD:.0f}.
          </p>
        </body></html>
        """

        try:
            _send_email("arielsteinberg2@gmail.com", subject, body)
            db.add(PriceAlert(
                event_id=event.id,
                alerted_at=datetime.datetime.utcnow(),
                price_at_alert=price,
            ))
            db.commit()
        except Exception as e:
            logger.error("Failed to send alert for %s: %s", event.name, e)
