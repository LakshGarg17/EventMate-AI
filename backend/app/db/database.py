import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings

DATABASE_URL = os.environ.get("DATABASE_URL") or settings.effective_database_url

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys and busy timeout on every SQLite connection."""
    try:
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
    # Import models to ensure they are registered with Base.metadata
    try:
        import app.db.models  # noqa: F401
    except ImportError:
        import backend.app.db.models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
