from datetime import date
from sqlalchemy import inspect, text
from app.db.database import Base, init_db
from app.db.models import Event, BudgetCategory, Expense, Task


def test_database_tables_exist(temp_db):
    engine = temp_db["engine"]
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    assert "events" in table_names
    assert "budget_categories" in table_names
    assert "expenses" in table_names
    assert "tasks" in table_names


def test_sqlite_fk_pragma_is_on(temp_db):
    engine = temp_db["engine"]
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1, "PRAGMA foreign_keys must be ON"


def test_init_db_is_idempotent_and_non_destructive(temp_db):
    engine = temp_db["engine"]
    SessionLocal = temp_db["SessionLocal"]

    # Insert an event
    with SessionLocal() as db:
        ev = Event(
            id="test-id-123",
            name="Original Event",
            event_type="Birthday",
            event_date=date(2026, 11, 15),
            location="Party Hall",
            guest_count=50,
            total_budget=5000000,
            currency="INR"
        )
        db.add(ev)
        db.commit()

    # Call init_db a second and third time
    init_db(target_engine=engine)
    init_db(target_engine=engine)

    # Verify original data is completely intact
    with SessionLocal() as db:
        fetched = db.get(Event, "test-id-123")
        assert fetched is not None
        assert fetched.name == "Original Event"
