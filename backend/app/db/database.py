import os
import re
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings

RAW_DATABASE_URL = os.environ.get("DATABASE_URL") or settings.effective_database_url


def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL connection URLs to the modern SQLAlchemy psycopg driver format
    while preserving SQLite, MySQL, and other dialect URLs as-is.
    """
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql+psycopg://" + trimmed[len("postgres://"):]
    if trimmed.startswith("postgresql://") and not trimmed.startswith("postgresql+"):
        return "postgresql+psycopg://" + trimmed[len("postgresql://"):]
    return trimmed


DATABASE_URL = normalize_database_url(RAW_DATABASE_URL)
is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {}
engine_kwargs = {}

if is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Production PostgreSQL resilience
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys and busy timeout only on SQLite connections."""
    try:
        # Check if this connection belongs to an SQLite driver
        driver_module = type(dbapi_connection).__module__
        if "sqlite" in driver_module:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    except Exception:
        pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None):
    """Idempotently creates all tables if they do not exist."""
    try:
        import app.db.models  # noqa: F401
    except ImportError:
        import backend.app.db.models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
