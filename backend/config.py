import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (one level up from backend/)
_root = Path(__file__).parent.parent
load_dotenv(_root / ".env")

TICKETMASTER_API_KEY: str = os.getenv("TICKETMASTER_API_KEY", "")
SEATGEEK_CLIENT_ID: str = os.getenv("SEATGEEK_CLIENT_ID", "")
TICKPICK_TOKEN: str = os.getenv("TICKPICK_TOKEN", "")
DB_PATH: str = os.getenv("DB_PATH", "data/prices.db")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")


def load_watchlist(path: Path = None) -> dict:
    """Return parsed watchlist.yaml as a dict."""
    if path is None:
        path = _root / "watchlist.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def get_search_targets(watchlist: dict) -> list[dict]:
    """
    Convert watchlist into a flat list of search targets.
    Each target: {"keyword": str, "classification": str, "category": str}
    """
    targets = []
    if watchlist.get("world_cup"):
        targets.append({
            "keyword": "World Cup 2026",
            "classification": "Sports",
            "category": "world_cup",
        })
    for artist in watchlist.get("concerts", []):
        targets.append({
            "keyword": artist,
            "classification": "Music",
            "category": "concerts",
        })
    for item in watchlist.get("events", []):
        targets.append({
            "keyword": item,
            "classification": None,
            "category": "events",
        })
    return targets
