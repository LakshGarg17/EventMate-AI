from datetime import date, datetime, timedelta, timezone
import json
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import select

from app.db.models import BudgetCategory, ChangeProposal, Event, Expense, Task, Vendor
from app.services.ai_service import AIService
from app.services.today import set_frozen_now, set_frozen_today


@pytest.fixture
def proposal_event(temp_db):
    SessionLocal = temp_db["SessionLocal"]
    with SessionLocal() as db:
        event = Event(
            name="Deepa & Sameer Reception",
            event_type="Wedding",
            event_date=date(2026, 12, 20),
            location="Grand Hyatt, Goa",
            guest_count=150,
            total_budget=60000000,  # 600,000.00 INR
            currency="INR",
            preferred_theme="Sunset Beach Elegance",
            additional_preferences="Cocktails and seafood BBQ",
            generated_plan={"overview": "Beachside wedding reception", "recommended_theme": {"name": "Sunset Beach"}},
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        cat1 = BudgetCategory(event_id=event.id, category_name="Venue", estimated_amount=25000000)
        cat2 = BudgetCategory(event_id=event.id, category_name="Catering", estimated_amount=20000000)
        cat3 = BudgetCategory(event_id=event.id, category_name="Decoration", estimated_amount=15000000)
        db.add_all([cat1, cat2, cat3])
        db.commit()

        t1 = Task(event_id=event.id, title="Confirm Beach Setup Permit", category="Permits", priority="High", due_date=date(2026, 11, 10), status="Pending")
        t2 = Task(event_id=event.id, title="Finalize Seafood Menu", category="Catering", priority="Medium", due_date=date(2026, 11, 25), status="Pending")
        db.add_all([t1, t2])
        db.commit()

        exp = Expense(event_id=event.id, budget_category_id=cat1.id, description="Beachfront Deposit", estimated_amount=10000000, actual_amount=10000000, payment_status="Paid")
        vendor = Vendor(event_id=event.id, name="Goa Sound & Lights", category="Entertainment", quoted_amount=5000000, status="Considering")
        db.add_all([exp, vendor])
        db.commit()

        event_id = event.id
    return event_id


def test_propose_changes_demo_mode_returns_503(client, proposal_event):
    with patch("app.config.settings.gemini_api_key", ""):
        res = client.post(
            f"/api/events/{proposal_event}/assistant/propose-changes",
            json={"message": "Move 20000 from Venue to Catering"},
        )
        assert res.status_code == 503
        assert "Plan modification requires a configured Gemini API key" in res.json()["detail"]


def test_propose_changes_clarification_path(client, proposal_event, temp_db):
    SessionLocal = temp_db["SessionLocal"]
    mock_json = """
    {
        "summary": "Clarification needed",
        "new_total_budget": null,
        "budget_adjustments": [],
        "tasks_to_add": [],
        "tasks_to_update": [],
        "clarification_question": "Which category would you like to reallocate the 20,000 from?"
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_json

    with patch("app.config.settings.gemini_api_key", "mock_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                res = client.post(
                    f"/api/events/{proposal_event}/assistant/propose-changes",
                    json={"message": "Please add 20000 to catering"},
                )
                assert res.status_code == 200
                data = res.json()
                assert data["proposal"] is None
                assert "Which category would you like" in data["clarification"]

                # Ensure NO ChangeProposal row is saved
                with SessionLocal() as db:
                    count = db.scalar(select(ChangeProposal).where(ChangeProposal.event_id == proposal_event))
                    assert count is None


def test_propose_changes_valid_creates_pending_proposal(client, proposal_event, temp_db, freeze_today):
    freeze_today(date(2026, 10, 30))
    SessionLocal = temp_db["SessionLocal"]

    mock_json = """
    {
        "summary": "Reallocate 20000 from Venue to Catering and add lighting task",
        "new_total_budget": null,
        "budget_adjustments": [
            {"category_name": "Venue", "delta_amount": "-20000"},
            {"category_name": "Catering", "delta_amount": "+20000"}
        ],
        "tasks_to_add": [
            {
                "title": "Install fairy lighting canopy",
                "description": "Over the beach seating area",
                "category": "Decoration",
                "priority": "High",
                "due_date": "2026-12-15"
            }
        ],
        "tasks_to_update": []
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_json

    with patch("app.config.settings.gemini_api_key", "mock_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                res = client.post(
                    f"/api/events/{proposal_event}/assistant/propose-changes",
                    json={"message": "Move 20000 from venue to catering and add lighting task"},
                )
                assert res.status_code == 200
                data = res.json()
                assert data["clarification"] is None
                proposal = data["proposal"]
                assert proposal["proposal_id"] is not None
                assert proposal["preview"]["budget"]["balanced"] is True
                assert len(proposal["preview"]["tasks_to_add"]) == 1

                # Verify ChangeProposal row in DB is pending
                with SessionLocal() as db:
                    db_prop = db.get(ChangeProposal, proposal["proposal_id"])
                    assert db_prop is not None
                    assert db_prop.status == "pending"
                    assert db_prop.base_fingerprint is not None

                    # Verify event, categories, and tasks are UNCHANGED
                    event_row = db.get(Event, proposal_event)
                    assert event_row.total_budget == 60000000
                    cat_venue = next(c for c in event_row.budget_categories if c.category_name == "Venue")
                    assert cat_venue.estimated_amount == 25000000  # unchanged!


def test_apply_proposal_flow_success_and_invariance(client, proposal_event, temp_db, freeze_today):
    freeze_today(date(2026, 10, 30))
    SessionLocal = temp_db["SessionLocal"]

    mock_json = """
    {
        "summary": "Reallocate 30000 from Decoration to Catering",
        "new_total_budget": null,
        "budget_adjustments": [
            {"category_name": "Decoration", "delta_amount": "-30000"},
            {"category_name": "Catering", "delta_amount": "+30000"}
        ],
        "tasks_to_add": [
            {
                "title": "Taste test grilled seafood skewers",
                "description": "At caterer kitchen",
                "category": "Catering",
                "priority": "Medium",
                "due_date": "2026-11-20"
            }
        ],
        "tasks_to_update": []
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_json

    with patch("app.config.settings.gemini_api_key", "mock_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                prop_res = client.post(
                    f"/api/events/{proposal_event}/assistant/propose-changes",
                    json={"message": "Move 30k from decor to catering"},
                )
                assert prop_res.status_code == 200
                prop_id = prop_res.json()["proposal"]["proposal_id"]

    # 1. Unconfirmed apply rejected (confirm: false)
    bad_res = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": False},
    )
    assert bad_res.status_code == 422

    # Capture before data for invariant assertions
    with SessionLocal() as db:
        ev_before = db.get(Event, proposal_event)
        exp_json_before = json.dumps([e.id for e in ev_before.expenses], sort_keys=True)
        vend_json_before = json.dumps([v.id for v in ev_before.vendors], sort_keys=True)
        plan_json_before = json.dumps(ev_before.generated_plan, sort_keys=True)
        cat_ids_before = {c.id for c in ev_before.budget_categories}

    # 2. Confirmed apply
    apply_res = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": True},
    )
    assert apply_res.status_code == 200
    data = apply_res.json()
    assert data["status"] == "applied"

    with SessionLocal() as db:
        ev_after = db.get(Event, proposal_event)
        # Check proposal marked applied
        prop_row = db.get(ChangeProposal, prop_id)
        assert prop_row.status == "applied"
        assert prop_row.applied_at is not None

        # Check category amounts updated in place (same IDs and count)
        cat_ids_after = {c.id for c in ev_after.budget_categories}
        assert cat_ids_before == cat_ids_after

        cat_decor = next(c for c in ev_after.budget_categories if c.category_name == "Decoration")
        cat_cater = next(c for c in ev_after.budget_categories if c.category_name == "Catering")
        assert cat_decor.estimated_amount == 12000000  # was 15000000 (-30000)
        assert cat_cater.estimated_amount == 23000000  # was 20000000 (+30000)

        # Invariance checks: Expenses, Vendors, Generated Plan byte-identical
        assert json.dumps([e.id for e in ev_after.expenses], sort_keys=True) == exp_json_before
        assert json.dumps([v.id for v in ev_after.vendors], sort_keys=True) == vend_json_before
        assert json.dumps(ev_after.generated_plan, sort_keys=True) == plan_json_before

        # Budget sum remains balanced
        cat_sum = sum(c.estimated_amount for c in ev_after.budget_categories)
        assert cat_sum == ev_after.total_budget

    # 3. Second apply returns 409
    second_res = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": True},
    )
    assert second_res.status_code == 409
    assert "already applied" in second_res.json()["detail"].lower()


def test_apply_stale_fingerprint_returns_409(client, proposal_event, temp_db, freeze_today):
    freeze_today(date(2026, 10, 30))
    SessionLocal = temp_db["SessionLocal"]

    mock_json = """
    {
        "summary": "Reallocate 10000 from Venue to Catering",
        "new_total_budget": null,
        "budget_adjustments": [
            {"category_name": "Venue", "delta_amount": "-10000"},
            {"category_name": "Catering", "delta_amount": "+10000"}
        ],
        "tasks_to_add": [],
        "tasks_to_update": []
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_json

    with patch("app.config.settings.gemini_api_key", "mock_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                prop_res = client.post(
                    f"/api/events/{proposal_event}/assistant/propose-changes",
                    json={"message": "Move 10k"},
                )
                assert prop_res.status_code == 200
                prop_id = prop_res.json()["proposal"]["proposal_id"]

    # Concurrently edit event total_budget to make fingerprint stale
    with SessionLocal() as db:
        ev = db.get(Event, proposal_event)
        ev.total_budget = 70000000  # change budget!
        db.commit()

    # Try apply -> expect 409 stale
    apply_res = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": True},
    )
    assert apply_res.status_code == 409
    assert "stale" in apply_res.json()["detail"].lower()


def test_apply_expired_proposal_returns_409(client, proposal_event, temp_db, freeze_now):
    SessionLocal = temp_db["SessionLocal"]
    now = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
    freeze_now(now)

    with SessionLocal() as db:
        prop = ChangeProposal(
            event_id=proposal_event,
            status="pending",
            user_message="Test expire",
            summary="Test expire summary",
            changes={"new_total_budget_minor": None, "category_deltas": [], "tasks_to_add": [], "tasks_to_update": []},
            preview={"budget": {"categories": [], "total_before": "600000.00", "total_after": "600000.00", "allocated_before": "600000.00", "allocated_after": "600000.00", "balanced": True}, "tasks_to_add": [], "tasks_to_update": [], "unchanged": "note"},
            base_fingerprint="abc",
            created_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)
        prop_id = prop.id

    # Fast forward time past 30 min
    freeze_now(now + timedelta(minutes=35))

    res = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": True},
    )
    assert res.status_code == 409
    assert "expired" in res.json()["detail"].lower()


def test_discard_proposal_and_foreign_event_check(client, proposal_event, temp_db):
    SessionLocal = temp_db["SessionLocal"]
    with SessionLocal() as db:
        # Create second event
        ev2 = Event(
            name="Other Event",
            event_type="Birthday",
            event_date=date(2026, 11, 20),
            location="Delhi",
            guest_count=20,
            total_budget=5000000,
            currency="INR",
        )
        db.add(ev2)
        db.commit()
        db.refresh(ev2)

        prop = ChangeProposal(
            event_id=proposal_event,
            status="pending",
            user_message="Test discard",
            summary="Discard test summary",
            changes={"new_total_budget_minor": None, "category_deltas": [], "tasks_to_add": [], "tasks_to_update": []},
            preview={"budget": {"categories": [], "total_before": "600000.00", "total_after": "600000.00", "allocated_before": "600000.00", "allocated_after": "600000.00", "balanced": True}, "tasks_to_add": [], "tasks_to_update": [], "unchanged": "note"},
            base_fingerprint="abc",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)
        prop_id = prop.id
        ev2_id = ev2.id

    # 1. Proposal from another event is 404
    res_foreign = client.post(
        f"/api/events/{ev2_id}/assistant/proposals/{prop_id}/discard",
    )
    assert res_foreign.status_code == 404

    # 2. Discard on correct event succeeds
    res_discard = client.post(
        f"/api/events/{proposal_event}/assistant/proposals/{prop_id}/discard",
    )
    assert res_discard.status_code == 200
    assert res_discard.json()["status"] == "discarded"

    # 3. Discarded proposal cannot be applied (409)
    res_apply = client.post(
        f"/api/events/{proposal_event}/assistant/apply-changes",
        json={"proposal_id": prop_id, "confirm": True},
    )
    assert res_apply.status_code == 409
    assert "discarded" in res_apply.json()["detail"].lower()

