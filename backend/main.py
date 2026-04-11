from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import init_db
from backend.routers.events import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from backend.scheduler import start_scheduler
    scheduler = start_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="Ticket Price Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
