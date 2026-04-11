# Ticket Price Tracker

Tracks lowest Ticketmaster prices daily for 2026 FIFA World Cup, concerts, and sports events. Shows trend charts and predicts the best time to buy.

## Setup

1. Install Python deps:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Install frontend deps:
   ```bash
   cd frontend && npm install
   ```

3. Edit `watchlist.yaml` to add concerts and sports events to track.

## Run

**Terminal 1 — backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend && npm run dev
```

Open http://localhost:3000

## How it works

- Prices are fetched from Ticketmaster automatically every day at 09:00.
- Click **↻ Fetch Now** in the UI to trigger a manual fetch at any time.
- After 3+ days of data per event, the dashboard shows a trend line and a BUY NOW / BUY SOON / WAIT recommendation.
- Edit `watchlist.yaml` and restart the backend to track new artists or sports teams.
