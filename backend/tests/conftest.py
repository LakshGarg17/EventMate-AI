import os
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

try:
    from app.db.database import Base, get_db
    from app.main import app
    from app.services.rate_limiter import ai_rate_limiter
    from app.services.today import set_frozen_now, set_frozen_today
except ImportError:
    from backend.app.db.database import Base, get_db
    from backend.app.main import app
    from backend.app.services.rate_limiter import ai_rate_limiter
    from backend.app.services.today import set_frozen_now, set_frozen_today


@pytest.fixture
def temp_db(tmp_path):
    """
    Creates a temporary SQLite database per test function,
    enables foreign keys, and initializes all tables.
    Never touches the production eventmate.db.
    """
    db_file = tmp_path / "test_eventmate.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    # Enable FKs and busy timeout explicitly for safety
    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    ai_rate_limiter.reset()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "SessionLocal": TestingSessionLocal,
        "db_file": db_file,
        "db_url": db_url,
    }

    # Teardown
    app.dependency_overrides.pop(get_db, None)
    set_frozen_today(None)
    set_frozen_now(None)
    ai_rate_limiter.reset()
    engine.dispose()


@pytest.fixture
def client(temp_db):
    """TestClient that uses the temporary isolated database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def freeze_today():
    """Helper fixture to freeze get_today() in tests."""
    def _freeze(frozen_date: date):
        set_frozen_today(frozen_date)
        return frozen_date

    yield _freeze
    set_frozen_today(None)


@pytest.fixture
def freeze_now():
    """Helper fixture to freeze get_now() in tests."""
    def _freeze(frozen_dt):
        set_frozen_now(frozen_dt)
        return frozen_dt

    yield _freeze
    set_frozen_now(None)
