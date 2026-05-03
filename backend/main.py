import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db import init_db
from backend.routers.events import router
from backend.routers.alerts import router as alerts_router

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache hashed assets forever (filenames change on rebuild so this is safe)
class CacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app.add_middleware(CacheStaticMiddleware)

app.include_router(router)
app.include_router(alerts_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built React frontend if dist/ exists (production)
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/og-image.png")
    def serve_og_image():
        return FileResponse(os.path.join(FRONTEND_DIST, "og-image.png"), media_type="image/png")

    _index_html = None

    @app.get("/{full_path:path}")
    def serve_frontend(request: Request, full_path: str):
        global _index_html
        if _index_html is None:
            with open(os.path.join(FRONTEND_DIST, "index.html"), encoding="utf-8") as f:
                _index_html = f.read()
        base = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
        html = _index_html.replace("__OG_BASE__", base)
        return HTMLResponse(html)
