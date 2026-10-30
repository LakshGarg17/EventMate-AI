from datetime import date, timedelta
from unittest.mock import patch
import pytest
from app.db.models import BudgetCategory, Event, Expense, Task


def test_create_event_without_plan(client):
    payload = {
        "name": "Minimalist Birthday",
        "event_type": "Birthday",
        "event_date": "2026-11-20",
        "location": "Home Rooftop",
        "guest_count": 25,
        "total_budget": "50000.00",
        "currency": "INR",
    }
    res = client.post("/api/events", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Minimalist Birthday"
    assert data["total_budget"] == "50000.00"
    assert data["budget_categories"] == []
    assert data["tasks"] == []
    assert data["budget_summary"]["total_budget"] == "50000.00"
    assert data["budget_summary"]["unallocated"] == "50000.00"


def test_create_event_with_plan_saves_categories_and_tasks(client):
    plan_mock = {
        "source": "gemini",
        "overview": "Grand celebration",
        "recommended_theme": {
            "name": "Royal Elegance",
            "description": "Rich gold and royal blue",
            "color_palette": ["#FFD700", "#002366"]
        },
        "budget": {
            "total_allocated": 10000000,
            "currency": "INR",
            "contingency": 700000,
            "items": [
                {"category": "Venue & Decor", "amount": 4000000, "percentage": 40.0, "notes": "Grand palace hall"},
                {"category": "Catering", "amount": 3500000, "percentage": 35.0, "notes": "Buffet for 150"},
                {"category": "Entertainment", "amount": 1000000, "percentage": 10.0, "notes": "Live Band"},
                {"category": "Venue & Decor", "amount": 800000, "percentage": 8.0, "notes": "Duplicate test"},
            ]
        },
        "timeline": [
            {
                "task": "Book Palace Venue",
                "description": "Lock in venue with advance payment",
                "priority": "High",
                "category": "Venue",
                "due_date": "2026-11-10",
                "days_before": 20
            },
            {
                "task": "Finalize Menu",
                "description": "Food tasting with caterer",
                "priority": "Medium",
                "category": "Catering",
                "due_date": "2026-11-15",
                "days_before": 15
            },
            {
                "task": "Invalid Date Task",
                "description": "Should be skipped with warning",
                "priority": "Low",
                "category": "General",
                "due_date": "invalid-date-string"
            }
        ],
        "checklist": ["Collect RSVPs"],
        "risks": []
    }

    payload = {
        "name": "Royal Wedding",
        "event_type": "Wedding",
        "event_date": "2026-11-30",
        "location": "Udaipur",
        "guest_count": 150,
        "total_budget": "100000.00",  # in major units: 100,000 INR
        "currency": "INR",
        "generated_plan": plan_mock
    }

    res = client.post("/api/events", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Royal Wedding"
    assert data["generated_plan"] == plan_mock  # plan JSON stored unchanged
    assert len(data["warnings"]) >= 1
    assert any("Invalid Date Task" in w for w in data["warnings"])

    # Verify categories sum to total budget exactly
    cats = data["budget_categories"]
    assert len(cats) > 0
    cat_names = [c["category_name"] for c in cats]
    # Check no duplicate category names
    assert len(cat_names) == len(set(cat_names))

    # All required categories + contingency should exist
    assert "Contingency Reserve" in cat_names
    # Category amounts parsed back to Decimal should sum exactly to 100000.00
    from decimal import Decimal
    cat_sum = sum(Decimal(c["estimated_amount"]) for c in cats)
    assert cat_sum == Decimal("100000.00")

    # Verify tasks created (2 valid, 1 invalid skipped)
    tasks = data["tasks"]
    assert len(tasks) == 2
    task_titles = [t["title"] for t in tasks]
    assert "Book Palace Venue" in task_titles
    assert "Finalize Menu" in task_titles
    assert "Invalid Date Task" not in task_titles


def test_create_event_atomic_rollback(client, temp_db):
    """Asserts that if an error occurs mid-save, nothing is persisted."""
    SessionLocal = temp_db["SessionLocal"]

    payload = {
        "name": "Rollback Test",
        "event_type": "Birthday",
        "event_date": "2026-12-01",
        "location": "Park",
        "guest_count": 20,
        "total_budget": "5000.00",
        "currency": "INR",
        "generated_plan": {
            "budget": {
                "items": [{"category": "Venue", "amount": 1000}]
            }
        }
    }

    # Inject failure during reconcile_budget
    with patch("app.api.routes.reconcile_budget", side_effect=RuntimeError("Simulated mid-save failure")):
        res = client.post("/api/events", json=payload)
        assert res.status_code == 500

    # Verify no Event was created in the database
    with SessionLocal() as db:
        events = db.query(Event).all()
        assert len(events) == 0


def test_get_event_and_list_summaries(client):
    # Create two events
    e1 = client.post("/api/events", json={
        "name": "Event One",
        "event_type": "Birthday",
        "event_date": "2026-11-10",
        "location": "NYC",
        "guest_count": 30,
        "total_budget": "1000.00",
        "currency": "USD"
    }).json()

    e2 = client.post("/api/events", json={
        "name": "Event Two",
        "event_type": "Community Event",
        "event_date": "2026-12-05",
        "location": "LA",
        "guest_count": 100,
        "total_budget": "5000.00",
        "currency": "USD"
    }).json()

    # Get single event
    res1 = client.get(f"/api/events/{e1['id']}")
    assert res1.status_code == 200
    assert res1.json()["id"] == e1["id"]

    # List summaries
    list_res = client.get("/api/events")
    assert list_res.status_code == 200
    summaries = list_res.json()
    assert len(summaries) >= 2
    # Newest first
    assert summaries[0]["id"] == e2["id"]
    assert summaries[1]["id"] == e1["id"]
    assert "task_counts" in summaries[0]
    assert "budget_utilization_percent" in summaries[0]


def test_put_event_constraints(client):
    created = client.post("/api/events", json={
        "name": "Modifiable Event",
        "event_type": "Birthday",
        "event_date": "2026-11-15",
        "location": "Austin",
        "guest_count": 40,
        "total_budget": "2500.00",
        "currency": "USD"
    }).json()
    event_id = created["id"]

    # 1. Reject id or generated_plan modification (extra="forbid" -> 422)
    bad_res1 = client.put(f"/api/events/{event_id}", json={"id": "new-id"})
    assert bad_res1.status_code == 422

    bad_res2 = client.put(f"/api/events/{event_id}", json={"generated_plan": {"test": 1}})
    assert bad_res2.status_code == 422

    # 2. Add an expense
    client.post(f"/api/events/{event_id}/expenses", json={
        "description": "Cake",
        "estimated_amount": "100.00",
        "payment_status": "Pending"
    })

    # 3. Currency change rejected when records exist
    curr_res = client.put(f"/api/events/{event_id}", json={"currency": "EUR"})
    assert curr_res.status_code == 422
    assert "Cannot change currency" in curr_res.json()["detail"]

    # 4. Valid update
    up_res = client.put(f"/api/events/{event_id}", json={
        "name": "Updated Event Title",
        "guest_count": 60,
        "total_budget": "3000.00"
    })
    assert up_res.status_code == 200
    updated_data = up_res.json()
    assert updated_data["name"] == "Updated Event Title"
    assert updated_data["guest_count"] == 60
    assert updated_data["total_budget"] == "3000.00"


def test_put_event_date_flags_tasks_after_event_date(client):
    created = client.post("/api/events", json={
        "name": "Date Shift Event",
        "event_type": "Wedding",
        "event_date": "2026-12-01",
        "location": "Boston",
        "guest_count": 50,
        "total_budget": "5000.00",
        "currency": "USD"
    }).json()
    event_id = created["id"]

    # Add task due on 2026-11-25
    t_res = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Vendor check",
        "category": "Vendors",
        "priority": "High",
        "due_date": "2026-11-25"
    })
    assert t_res.status_code == 201
    assert t_res.json()["after_event_date"] is False

    # Move event date to 2026-11-20 (before task due date)
    up_res = client.put(f"/api/events/{event_id}", json={"event_date": "2026-11-20"})
    assert up_res.status_code == 200
    task_in_resp = up_res.json()["tasks"][0]
    assert task_in_resp["after_event_date"] is True


def test_delete_event_cascades_and_preserves_unrelated(client, temp_db):
    SessionLocal = temp_db["SessionLocal"]

    e1 = client.post("/api/events", json={
        "name": "Event to Delete",
        "event_type": "Birthday",
        "event_date": "2026-11-10",
        "location": "Venue 1",
        "guest_count": 10,
        "total_budget": "1000.00",
        "currency": "USD"
    }).json()

    e2 = client.post("/api/events", json={
        "name": "Keeper Event",
        "event_type": "Birthday",
        "event_date": "2026-11-10",
        "location": "Venue 2",
        "guest_count": 10,
        "total_budget": "1000.00",
        "currency": "USD"
    }).json()

    # Add expense and task to both
    client.post(f"/api/events/{e1['id']}/expenses", json={"description": "E1 Exp", "estimated_amount": "50.00"})
    client.post(f"/api/events/{e1['id']}/tasks", json={"title": "E1 Task", "category": "General", "due_date": "2026-11-05"})

    client.post(f"/api/events/{e2['id']}/expenses", json={"description": "E2 Exp", "estimated_amount": "80.00"})
    client.post(f"/api/events/{e2['id']}/tasks", json={"title": "E2 Task", "category": "General", "due_date": "2026-11-05"})

    # Delete e1
    del_res = client.delete(f"/api/events/{e1['id']}")
    assert del_res.status_code == 204

    # Verify e1 is 404
    assert client.get(f"/api/events/{e1['id']}").status_code == 404

    # Verify in DB that e1's rows are gone and e2's rows remain
    with SessionLocal() as db:
        assert db.query(Expense).filter(Expense.event_id == e1["id"]).count() == 0
        assert db.query(Task).filter(Task.event_id == e1["id"]).count() == 0

        assert db.query(Event).filter(Event.id == e2["id"]).count() == 1
        assert db.query(Expense).filter(Expense.event_id == e2["id"]).count() == 1
        assert db.query(Task).filter(Task.event_id == e2["id"]).count() == 1


def test_malformed_id_returns_404(client):
    assert client.get("/api/events/nonexistent-uuid-1234").status_code == 404
    assert client.get("/api/events/invalid-id-malformed-999").status_code == 404
    assert client.put("/api/events/invalid-id-malformed-999", json={"name": "Test"}).status_code == 404
    assert client.delete("/api/events/invalid-id-malformed-999").status_code == 404
