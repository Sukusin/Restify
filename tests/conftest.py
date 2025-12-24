import os
import tempfile
from pathlib import Path

_tmpdir = Path(tempfile.mkdtemp(prefix="restify_test_"))
_db_path = _tmpdir / "test.db"

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path.as_posix()}")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LLM_PROVIDER", "disabled")
os.environ.setdefault("GEOAPIFY_KEY", "")

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import create_app
from app.core.rate_limit import _reset_for_tests


@pytest.fixture()
def clean_db():
    _reset_for_tests()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
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
