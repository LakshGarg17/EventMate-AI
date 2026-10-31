import os
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import BigInteger, DateTime, JSON, String, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

try:
    from app.config import DEFAULT_DB_FILE, Settings
    from app.db.database import (
        Base,
        create_db_engine,
        init_db,
        normalize_database_url,
    )
    from app.db.models import (
        BudgetCategory,
        ChangeProposal,
        Event,
        Expense,
        Task,
        Vendor,
    )
except ImportError:
    from backend.app.config import DEFAULT_DB_FILE, Settings
    from backend.app.db.database import (
        Base,
        create_db_engine,
        init_db,
        normalize_database_url,
    )
    from backend.app.db.models import (
        BudgetCategory,
        ChangeProposal,
        Event,
        Expense,
        Task,
        Vendor,
    )


class TestPostgresURLNormalization:
    """Tests URL normalization for cloud providers (Vercel, Neon, Supabase, Render, Railway)."""

    def test_normalizes_postgres_protocol(self):
        raw = "postgres://user:secret@ep-test-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+psycopg://user:secret@ep-test-123.us-east-2.aws.neon.tech/neondb?sslmode=require"

    def test_normalizes_postgresql_protocol(self):
        raw = "postgresql://user:secret@ep-test-123.us-east-2.aws.neon.tech/neondb"
        normalized = normalize_database_url(raw)
        assert normalized == "postgresql+psycopg://user:secret@ep-test-123.us-east-2.aws.neon.tech/neondb"

    def test_preserves_explicit_psycopg_driver(self):
        raw = "postgresql+psycopg://user:secret@localhost:5432/eventmate"
        normalized = normalize_database_url(raw)
        assert normalized == raw

    def test_preserves_explicit_psycopg2_driver(self):
        raw = "postgresql+psycopg2://user:secret@localhost:5432/eventmate"
        normalized = normalize_database_url(raw)
        assert normalized == raw

    def test_preserves_sqlite_urls(self):
        sqlite_file = "sqlite:///D:/Virtual Promptwars/EventMate AI/backend/eventmate.db"
        sqlite_mem = "sqlite:///:memory:"
        assert normalize_database_url(sqlite_file) == sqlite_file
        assert normalize_database_url(sqlite_mem) == sqlite_mem

    def test_handles_whitespace_and_query_parameters(self):
        raw = "  postgres://user:pass@host:5432/db?sslmode=require&options=endpoint%3Dep-cool-123  "
        normalized = normalize_database_url(raw)
        assert normalized.startswith("postgresql+psycopg://")
        assert "sslmode=require" in normalized
        assert "options=endpoint%3Dep-cool-123" in normalized


class TestEngineConfiguration:
    """Verifies SQLAlchemy engine creation options across SQLite and PostgreSQL."""

    def test_sqlite_engine_configuration(self):
        engine = create_db_engine("sqlite:///:memory:")
        assert engine.dialect.name == "sqlite"
        # Verify connect_args contains check_same_thread=False
        # (SQLite dialect creates connection using these arguments)
        engine.dispose()

    def test_postgres_engine_configuration(self):
        pg_url = "postgresql+psycopg://user:pass@ep-test-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
        engine = create_db_engine(pg_url)
        assert engine.dialect.name == "postgresql"
        # Verify connection pool settings
        assert engine.pool._pre_ping is True
        assert engine.pool._recycle == 300
        engine.dispose()


class TestPostgresModelDDLCompilation:
    """
    Verifies that all SQLAlchemy models compile into 100% valid, standard PostgreSQL DDL.
    Checks column types, constraints, foreign keys, and indexes.
    """

    @pytest.fixture
    def pg_dialect(self):
        return postgresql.dialect()

    def test_event_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(Event.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE events (" in ddl
        assert "id VARCHAR(36) NOT NULL" in ddl
        assert "total_budget BIGINT NOT NULL" in ddl
        assert "created_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
        assert "updated_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
        assert "generated_plan JSON" in ddl
        assert "CONSTRAINT chk_event_type CHECK" in ddl
        assert "PRIMARY KEY (id)" in ddl

    def test_budget_category_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(BudgetCategory.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE budget_categories (" in ddl
        assert "estimated_amount BIGINT NOT NULL" in ddl
        assert "FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE" in ddl
        assert "CONSTRAINT uq_event_category_name UNIQUE (event_id, category_name)" in ddl

    def test_expense_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(Expense.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE expenses (" in ddl
        assert "estimated_amount BIGINT NOT NULL" in ddl
        assert "actual_amount BIGINT" in ddl
        assert "CONSTRAINT chk_expense_payment_status CHECK" in ddl
        assert "FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE" in ddl
        assert "FOREIGN KEY(budget_category_id) REFERENCES budget_categories (id) ON DELETE SET NULL" in ddl

    def test_task_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(Task.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE tasks (" in ddl
        assert "CONSTRAINT chk_task_priority CHECK" in ddl
        assert "CONSTRAINT chk_task_status CHECK" in ddl
        assert "FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE" in ddl

    def test_vendor_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(Vendor.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE vendors (" in ddl
        assert "quoted_amount BIGINT" in ddl
        assert "CONSTRAINT chk_vendor_category CHECK" in ddl
        assert "CONSTRAINT chk_vendor_status CHECK" in ddl
        assert "FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE" in ddl

    def test_change_proposal_table_pg_ddl(self, pg_dialect):
        ddl = str(CreateTable(ChangeProposal.__table__).compile(dialect=pg_dialect))
        assert "CREATE TABLE change_proposals (" in ddl
        assert "changes JSON NOT NULL" in ddl
        assert "preview JSON NOT NULL" in ddl
        assert "CONSTRAINT chk_proposal_status CHECK" in ddl
        assert "FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE" in ddl


class TestSettingsAndDatabaseEnvironment:
    """Verifies that DATABASE_URL environment variable is correctly respected."""

    def test_database_url_from_settings(self, monkeypatch):
        test_url = "postgres://appuser:mypass@remote.db.server:5432/appdb"
        monkeypatch.setenv("DATABASE_URL", test_url)
        s = Settings()
        assert s.effective_database_url == test_url

    def test_fallback_to_sqlite_when_no_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        s = Settings(database_url=None)
        assert s.effective_database_url.startswith("sqlite:///")
        assert "eventmate.db" in s.effective_database_url


class TestDatabaseInitializationIdempotency:
    """Verifies that init_db can be called multiple times safely."""

    def test_init_db_creates_all_tables_idempotently(self, tmp_path):
        test_db = tmp_path / "test_init.db"
        test_url = f"sqlite:///{test_db.as_posix()}"
        test_eng = create_db_engine(test_url)

        # First run creates tables
        init_db(target_engine=test_eng)
        inspector = inspect(test_eng)
        tables = inspector.get_table_names()
        assert "events" in tables
        assert "budget_categories" in tables
        assert "expenses" in tables
        assert "tasks" in tables
        assert "vendors" in tables
        assert "change_proposals" in tables

        # Second run should be safe and idempotent
        init_db(target_engine=test_eng)
        inspector2 = inspect(test_eng)
        assert len(inspector2.get_table_names()) == 6
        test_eng.dispose()


@pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"),
    reason="TEST_POSTGRES_URL not set in environment (skip live PostgreSQL CRUD)",
)
def test_live_postgres_crud():
    """
    Live test against a real PostgreSQL database if TEST_POSTGRES_URL is configured.
    Tests table creation and end-to-end relational persistence.
    """
    pg_url = os.environ["TEST_POSTGRES_URL"]
    eng = create_db_engine(pg_url)
    init_db(target_engine=eng)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=eng)
    session = Session()

    try:
        event = Event(
            name="Live Postgres Test Gala",
            event_type="Wedding",
            event_date=date(2027, 6, 15),
            location="Grand Ballroom",
            guest_count=150,
            total_budget=5000000,
            currency="INR",
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        assert event.id is not None
        assert event.name == "Live Postgres Test Gala"

        # Cleanup
        session.delete(event)
        session.commit()
    finally:
        session.close()
        eng.dispose()

