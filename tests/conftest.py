import os
import tempfile
from pathlib import Path

# IMPORTANT: set env vars BEFORE importing app modules (settings/engine are created at import time)
_tmpdir = Path(tempfile.mkdtemp(prefix="restify_test_"))
_db_path = _tmpdir / "test.db"

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path.as_posix()}")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LLM_PROVIDER", "disabled")  # avoid HF downloads
os.environ.setdefault("GEOAPIFY_KEY", "")          # skip Geoapify import

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import create_app
from app.core.rate_limit import _reset_for_tests


@pytest.fixture()
def clean_db():
    # reset rate limiter between tests (global state)
    _reset_for_tests()

    # Fresh DB schema for each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # keep db file for debugging; drop tables to avoid cross-test interference
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(clean_db):
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def client(clean_db):
    app = create_app()
    with TestClient(app) as c:
        yield c


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
