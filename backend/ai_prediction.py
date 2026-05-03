"""
AI-powered ticket price prediction using Claude.

Sends price history and event context to Claude, which reasons about
supply/demand dynamics, event urgency, and trend patterns.

Falls back to the rule-based prediction if the API is unavailable.
"""
import datetime
import json
import logging
from typing import Optional

from backend.prediction import Prediction, predict as rule_based_predict

logger = logging.getLogger(__name__)


def ai_predict(
    prices: list[tuple[datetime.date, float]],
    event_name: str,
    event_date: Optional[datetime.date] = None,
) -> Optional[Prediction]:
    from backend.config import ANTHROPIC_API_KEY

    rule_result = rule_based_predict(prices, event_date=event_date)

    if not ANTHROPIC_API_KEY:
        return rule_result

    # Only call AI when rule-based has enough data to give useful context
    if rule_result is None:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        today = datetime.date.today()
        days_until = (event_date - today).days if event_date else None

        # Deduplicate to daily prices for cleaner prompt
        daily: dict[datetime.date, float] = {}
        for d, p in prices:
            daily[d] = p
        daily_prices = sorted(daily.items())

        history_lines = "\n".join(
            f"  {d.isoformat()}: ${p:.2f}"
            for d, p in daily_prices[-30:]
        )

        current_price = daily_prices[-1][1]
        price_min = min(p for _, p in daily_prices)
        price_max = max(p for _, p in daily_prices)

        prompt = f"""You are a ticket pricing analyst. Analyze this price history and give your best prediction.

EVENT: {event_name}
Event date: {event_date.isoformat() if event_date else 'Unknown'}
Days until event: {days_until if days_until is not None else 'Unknown'}
Today: {today.isoformat()}

DAILY PRICE HISTORY (most recent last):
{history_lines}

STATS:
- Current: ${current_price:.2f}
- All-time low: ${price_min:.2f}
- All-time high: ${price_max:.2f}
- Days of data: {len(daily_prices)}

RULE-BASED MODEL:
- Trend: {rule_result.trend}
- Recommendation: {rule_result.recommendation}
- 7-day projection: ${rule_result.predicted_price_7d:.2f}
- Confidence: {rule_result.confidence}

Consider:
1. Is the current price cheap or expensive relative to history?
2. Is the trend likely to continue or reverse?
3. Time pressure — how urgent is it to buy given days until event?
4. For World Cup / high-demand events: prices spike near event date.
5. How confident are you given the data quality (days tracked, price variation)?

Respond ONLY with JSON:
{{
  "predicted_price_7d": <float>,
  "recommendation": "<BUY NOW | BUY SOON | WAIT>",
  "trend": "<rising | falling | flat>",
  "confidence": "<low | medium | high>",
  "reasoning": "<1-2 sentences>"
}}"""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        text = next(
            (block.text for block in response.content if block.type == "text"), ""
        ).strip()

        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)

        predicted_price = float(data["predicted_price_7d"])
        recommendation = data["recommendation"].upper().strip()
        trend = data["trend"].lower().strip()
        confidence = data.get("confidence", rule_result.confidence).lower().strip()

        if recommendation not in ("BUY NOW", "BUY SOON", "WAIT"):
            recommendation = rule_result.recommendation
        if trend not in ("rising", "falling", "flat"):
            trend = rule_result.trend
        if confidence not in ("low", "medium", "high"):
            confidence = rule_result.confidence

        logger.info(
            "AI prediction for '%s': %s @ $%.0f [%s] — %s",
            event_name, recommendation, predicted_price, confidence,
            data.get("reasoning", ""),
        )

        return Prediction(
            trend=trend,
            predicted_price_7d=round(predicted_price, 2),
            recommendation=recommendation,
            slope=rule_result.slope,
            score=rule_result.score,
            confidence=confidence,
        )

    except Exception as e:
        logger.warning("AI prediction failed, falling back to rule-based: %s", e)
        return rule_result
