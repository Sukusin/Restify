from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.base import Base
from app.db.session import engine

import app.models

from app.routers import auth, users, places, reviews, recommendations, chat
from app.parsers.geoapify_importer import import_places_on_startup

configure_logging(log_dir=settings.log_dir, level=settings.log_level)
logger = logging.getLogger(__name__)


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-store"
        return resp


def create_app() -> FastAPI:
    app = FastAPI(title="Leisure Recommender", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        logger.info("DB ready")

        try:
            await import_places_on_startup()
        except Exception:
            logger.exception("Places import failed")

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

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(places.router)
    app.include_router(reviews.router)
    app.include_router(recommendations.router)
    app.include_router(chat.router)

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        files_cls = DevStaticFiles if getattr(settings, "debug", False) else StaticFiles
        app.mount("/ui", files_cls(directory=str(static_dir), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


app = create_app()
