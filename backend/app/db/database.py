import os
import re
from pathlib import Path
from typing import Optional
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


def create_db_engine(url: Optional[str] = None):
    """
    Creates a configured SQLAlchemy Engine.
    For PostgreSQL: configures connection pooling resilience (pre-ping, 300s recycle, 5 pool size, 10 overflow)
    suitable for serverless, Neon, Render, Supabase, and cloud platforms.
    For SQLite: disables thread-checking for multi-threaded FastAPI workers.
    """
    target_url = normalize_database_url(url) if url else DATABASE_URL
    connect_args = {}
    engine_kwargs = {}

    if target_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        # Production PostgreSQL resilience (e.g. Neon, Supabase, Vercel Postgres, Render)
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    return create_engine(target_url, connect_args=connect_args, **engine_kwargs)


engine = create_db_engine()



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
