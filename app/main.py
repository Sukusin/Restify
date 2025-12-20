from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.session import engine
from app.db.base import Base

import app.models  # noqa: F401  (register models)

from app.routers import auth, users, places, reviews, recommendations, chat

# Configure logging as early as possible
configure_logging(log_dir=settings.log_dir, level=settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Leisure Recommender", version="0.1.0")

    # CORS is enabled for simple local development scenarios:
    # - serving UI separately (Live Server)
    # - opening index.html from file://
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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
        except Exception as exc:
            logger.exception("Unhandled error")
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        duration_ms = int((time.time() - start) * 1000)
        logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
        return response

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(places.router)
    app.include_router(reviews.router)
    app.include_router(recommendations.router)
    app.include_router(chat.router)

    # Serve the provided minimal HTML UI
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


app = create_app()
