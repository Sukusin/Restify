from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.session import engine
from app.db.base import Base

import app.models  # noqa: F401  (register models)

from app.routers import auth, users, places, reviews, recommendations, chat, moderation

# Configure logging as early as possible
configure_logging(log_dir=settings.log_dir, level=settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Leisure Recommender", version="0.1.0")

    # ---------- CORS (нужно только если UI открываешь НЕ с бэкенда, например через Live Server) ----------
    # Если всегда открываешь http://127.0.0.1:8000/ui/ — можешь удалить этот блок.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        # Create tables (minimal replacement for migrations)
        Base.metadata.create_all(bind=engine)
        logger.info("DB ready")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error")
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        duration_ms = int((time.time() - start) * 1000)
        logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
        return response

    # ---------- Static UI ----------
    # repo_root/app/main.py -> repo_root
    repo_root = Path(__file__).resolve().parents[2]
    ui_dir = repo_root / "frontend"

    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def root() -> FileResponse:
            return FileResponse(ui_dir / "index.html")
    else:
        logger.warning("UI directory not found: %s (skip mounting /ui)", ui_dir)

    # ---------- API routers ----------
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(places.router)
    app.include_router(reviews.router)
    app.include_router(recommendations.router)
    app.include_router(chat.router)
    app.include_router(moderation.router)

    return app


app = create_app()
