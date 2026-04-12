"""
AI-powered ticket price prediction using Claude Opus 4.6.

Sends price history and event context to Claude, which reasons about
supply/demand dynamics, event urgency, and trend patterns to produce
an optimized recommendation and predicted price.

Falls back to the rule-based Prediction object if the API is unavailable.
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
    """
    Use Claude Opus 4.6 to produce an optimized price prediction.

    Returns a Prediction dataclass (same interface as rule-based predict()).
    Falls back to rule-based predict() if API key is missing or call fails.
    """
    from backend.config import ANTHROPIC_API_KEY

    # Always compute the rule-based result — used as fallback and as context for Claude
    rule_result = rule_based_predict(prices, event_date=event_date)

    if not ANTHROPIC_API_KEY:
        return rule_result

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        today = datetime.date.today()
        days_until = (event_date - today).days if event_date else None

        # Format price history for Claude
        history_lines = "\n".join(
            f"  {date.isoformat()}: ${price:.2f}"
            for date, price in prices[-30:]  # last 30 data points
        )

        current_price = prices[-1][1] if prices else None
        price_min = min(p for _, p in prices) if prices else None
        price_max = max(p for _, p in prices) if prices else None

        prompt = f"""You are a ticket pricing analyst specializing in live event markets.
Analyze this ticket price history and provide your best prediction.

EVENT: {event_name}
Event date: {event_date.isoformat() if event_date else 'Unknown'}
Days until event: {days_until if days_until is not None else 'Unknown'}
Today: {today.isoformat()}

PRICE HISTORY (most recent last):
{history_lines}

CURRENT STATS:
- Current price: ${current_price:.2f}
- All-time low: ${price_min:.2f}
- All-time high: ${price_max:.2f}
- Data points: {len(prices)}

RULE-BASED SYSTEM SAYS:
- Trend: {rule_result.trend if rule_result else 'unknown'}
- Score: {rule_result.score if rule_result else 'N/A'}/10
- Rule recommendation: {rule_result.recommendation if rule_result else 'unknown'}
- Rule 7-day price projection: ${rule_result.predicted_price_7d:.2f if rule_result else 'N/A'}

Your task: Give an OPTIMIZED prediction. Consider:
1. Ticket market dynamics (prices often rise near event date, drop after initial rush)
2. Whether this price is historically cheap or expensive for this event
3. The urgency given days until event
4. Whether the current trend is likely to continue or reverse
5. For World Cup games: high-demand matches (knockouts, Argentina, Brazil) behave differently

Respond ONLY with a JSON object in this exact format:
{{
  "predicted_price_7d": <float, your best estimate of price in 7 days>,
  "recommendation": "<one of: BUY NOW, BUY SOON, WAIT>",
  "trend": "<one of: rising, falling, flat>",
  "reasoning": "<1-2 sentence explanation>"
}}"""

        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text response
        text = next(
            (block.text for block in response.content if block.type == "text"), ""
        ).strip()

        # Parse JSON from response
        # Claude might wrap in ```json ... ``` — strip that
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)

        predicted_price = float(data["predicted_price_7d"])
        recommendation = data["recommendation"].upper().strip()
        trend = data["trend"].lower().strip()

        # Validate values
        if recommendation not in ("BUY NOW", "BUY SOON", "WAIT"):
            recommendation = rule_result.recommendation if rule_result else "WAIT"
        if trend not in ("rising", "falling", "flat"):
            trend = rule_result.trend if rule_result else "flat"

        logger.info(
            "AI prediction for '%s': %s @ $%.0f (rule was %s @ $%.0f) — %s",
            event_name,
            recommendation,
            predicted_price,
            rule_result.recommendation if rule_result else "N/A",
            rule_result.predicted_price_7d if rule_result else 0,
            data.get("reasoning", ""),
        )

        return Prediction(
            trend=trend,
            predicted_price_7d=round(predicted_price, 2),
            recommendation=recommendation,
            slope=rule_result.slope if rule_result else 0.0,
            score=rule_result.score if rule_result else 0,
        )

    except Exception as e:
        logger.warning("AI prediction failed, falling back to rule-based: %s", e)
        return rule_result
