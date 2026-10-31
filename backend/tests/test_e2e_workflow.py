import asyncio
from datetime import date, datetime, timedelta, timezone
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from google.genai import errors
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.db.models import BudgetCategory, ChangeProposal, Event, Expense, Task, Vendor
from app.main import app
from app.schemas import AIProposalResponse
from app.services.ai_service import AIService
from app.services.rate_limiter import ai_rate_limiter
from app.services.today import set_frozen_now, set_frozen_today


def test_complete_e2e_user_journey_workflow(tmp_path, freeze_today, freeze_now):
    """
    Comprehensive End-to-End Test walking the full user journey:
    1. Generate plan (mocked).
    2. Save as event.
    3. Reload through a new app instance against the same SQLite file to verify persistence.
    4. Update event parameters.
    5. Add, edit, delete expenses; verify exact minor-unit totals, budget utilization, and over-budget calculation.
    6. Add, update, complete tasks; verify progress percentage and overdue flags.
    7. Add, update status, and delete vendors; verify category quotation comparison and selected total.
    8. Ask assistant in Ask mode; assert database row counts remain completely unchanged.
    9. Propose changes in Modify mode; verify preview; confirm and apply; assert only categories and tasks changed,
       while expenses, vendors, and generated plan are untouched; assert duplicate apply returns 409 Conflict.
    10. Generate themes and bilingual invitations (English & Hindi).
    11. Verify Gemini failure mapping (504 timeout, 429/503 quota, 502 bad format, 500 generic).
    12. Verify demo mode labels and behavior without API key.
    13. Delete event; verify cascading deletion of all child rows (categories, expenses, tasks, vendors, proposals)
        while preserving other events.
    """
    today = date(2026, 10, 31)
    freeze_today(today)
    freeze_now(datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc))

    db_file = tmp_path / "e2e_test_workflow.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    ai_rate_limiter.reset()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            # -------------------------------------------------------------
            # STEP 1: Generate plan (mocked Gemini response)
            # -------------------------------------------------------------
            mock_plan_payload = {
                "overview": "A grand royal Marwar sangeet celebration in Udaipur.",
                "recommended_theme": {
                    "name": "Royal Marwar",
                    "description": "Rich crimson and gold heritage aesthetic.",
                    "color_palette": ["#B91C1C", "#F59E0B", "#FDF2E9"],
                },
                "budget_items": [
                    {"category": "Venue", "estimated_amount": 150000, "notes": "Palace courtyards"},
                    {"category": "Catering", "estimated_amount": 150000, "notes": "Royal feast"},
                    {"category": "Decoration", "estimated_amount": 75000, "notes": "Marigold floral decor"},
                    {"category": "Entertainment", "estimated_amount": 40000, "notes": "Folk performers"},
                    {"category": "Photography", "estimated_amount": 35000, "notes": "Portraits"},
                    {"category": "Miscellaneous", "estimated_amount": 15000, "notes": "Gifts"},
                    {"category": "Contingency Reserve", "estimated_amount": 35000, "notes": "Buffer"},
                ],
                "checklist": ["Book heritage venue", "Hire royal caterers"],
                "timeline": [
                    {
                        "task": "Book Palace Venue",
                        "description": "Deposit for courtyards",
                        "priority": "High",
                        "category": "Venue",
                        "days_before": 15,
                    },
                    {
                        "task": "Hire Shehnai Troupe",
                        "description": "Book traditional musicians",
                        "priority": "Medium",
                        "category": "Entertainment",
                        "days_before": 10,
                    },
                ],
                "decoration_suggestions": ["Marigold canopies", "Brass lanterns"],
                "catering_suggestions": ["Dal Baati Churma", "Kesar Pista Kulfi"],
                "entertainment_suggestions": ["Ghoomar dancers", "Live shehnai"],
                "vendor_requirements": ["Florist", "A/V technician"],
                "risks": [{"risk": "Evening chill", "likelihood": "Low", "mitigation": "Outdoor heaters"}],
                "warnings": [],
            }

            mock_response = MagicMock()
            mock_response.text = json.dumps(mock_plan_payload)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_response

                    gen_res = client.post(
                        "/api/events/generate",
                        json={
                            "event_name": "Priya's Grand Sangeet",
                            "event_type": "Wedding",
                            "event_date": "2026-11-20",
                            "location": "Udaipur",
                            "guest_count": 120,
                            "total_budget": 500000,
                            "currency": "INR",
                        },
                    )
                    assert gen_res.status_code == 200
                    plan_data = gen_res.json()
                    assert plan_data["source"] == "gemini"
                    assert plan_data["budget"]["total_allocated"] == 500000
                    assert len(plan_data["budget"]["items"]) == 7
                    assert len(plan_data["timeline"]) == 2

            # -------------------------------------------------------------
            # STEP 2: Save as event with budget categories and tasks
            # -------------------------------------------------------------
            create_payload = {
                "name": "Priya's Grand Sangeet",
                "event_type": "Wedding",
                "event_date": "2026-11-20",
                "location": "Udaipur",
                "guest_count": 120,
                "total_budget": "500000.00",
                "currency": "INR",
                "preferred_theme": "Royal Marwar",
                "additional_preferences": "Authentic Rajasthani cuisine",
                "generated_plan": plan_data,
            }
            create_res = client.post("/api/events", json=create_payload)
            assert create_res.status_code == 201
            event_id = create_res.json()["id"]
            assert event_id is not None
            assert create_res.json()["total_budget"] == "500000.00"
            assert len(create_res.json()["budget_categories"]) == 7
            assert len(create_res.json()["tasks"]) == 2

            # Retrieve category IDs
            cat_map = {c["category_name"]: c["id"] for c in create_res.json()["budget_categories"]}
            venue_cat_id = cat_map["Venue"]
            catering_cat_id = cat_map["Catering"]
            assert venue_cat_id is not None
            assert catering_cat_id is not None

        # -------------------------------------------------------------
        # STEP 3: Reload through a new app instance against same SQLite file
        # -------------------------------------------------------------
        fresh_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        FreshSession = sessionmaker(autocommit=False, autoflush=False, bind=fresh_engine)

        def fresh_override_get_db():
            db = FreshSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = fresh_override_get_db

        with TestClient(app) as fresh_client:
            reload_res = fresh_client.get(f"/api/events/{event_id}")
            assert reload_res.status_code == 200
            reloaded_event = reload_res.json()
            assert reloaded_event["name"] == "Priya's Grand Sangeet"
            assert reloaded_event["total_budget"] == "500000.00"
            assert len(reloaded_event["budget_categories"]) == 7
            assert len(reloaded_event["tasks"]) == 2

            # -------------------------------------------------------------
            # STEP 4: Update event parameters
            # -------------------------------------------------------------
            update_res = fresh_client.put(
                f"/api/events/{event_id}",
                json={
                    "guest_count": 130,
                    "location": "Udaipur Palace Courtyard",
                },
            )
            assert update_res.status_code == 200
            updated_data = update_res.json()
            assert updated_data["guest_count"] == 130
            assert updated_data["location"] == "Udaipur Palace Courtyard"

            # -------------------------------------------------------------
            # STEP 5: Expenses CRUD, minor-unit totals, budget utilization & over-budget
            # -------------------------------------------------------------
            # Add Expense 1: Venue Advance (100,000 INR)
            exp1_res = fresh_client.post(
                f"/api/events/{event_id}/expenses",
                json={
                    "description": "Venue Advance Deposit",
                    "budget_category_id": venue_cat_id,
                    "estimated_amount": "100000.00",
                    "actual_amount": "100000.00",
                    "payment_status": "Paid",
                },
            )
            assert exp1_res.status_code == 201
            exp1_id = exp1_res.json()["id"]

            # Add Expense 2: Catering Tasting (10,000 estimated, 12,000 actual)
            exp2_res = fresh_client.post(
                f"/api/events/{event_id}/expenses",
                json={
                    "description": "Catering Menu Tasting",
                    "budget_category_id": catering_cat_id,
                    "estimated_amount": "10000.00",
                    "actual_amount": "12000.00",
                    "payment_status": "Paid",
                },
            )
            assert exp2_res.status_code == 201
            exp2_id = exp2_res.json()["id"]

            # Check Budget Summary: Total actual = 112,000 / 500,000 = 22.4%
            ev_detail1 = fresh_client.get(f"/api/events/{event_id}").json()
            b_sum1 = ev_detail1["budget_summary"]
            assert b_sum1["total_budget"] == "500000.00"
            assert b_sum1["total_estimated"] == "110000.00"
            assert b_sum1["total_actual"] == "112000.00"
            assert b_sum1["utilization_percent"] == 22.4
            assert b_sum1["over_budget"] is False

            # Edit Expense 2: Increase actual amount to 15,000.00
            exp2_edit = fresh_client.put(
                f"/api/expenses/{exp2_id}",
                json={"actual_amount": "15000.00"},
            )
            assert exp2_edit.status_code == 200
            assert exp2_edit.json()["actual_amount"] == "15000.00"

            ev_detail2 = fresh_client.get(f"/api/events/{event_id}").json()
            assert ev_detail2["budget_summary"]["total_actual"] == "115000.00"
            assert ev_detail2["budget_summary"]["utilization_percent"] == 23.0

            # Add Expense 3 to trigger over-budget: 450,000 actual (115,000 + 450,000 = 565,000 > 500,000)
            exp3_res = fresh_client.post(
                f"/api/events/{event_id}/expenses",
                json={
                    "description": "Massive Ballroom Splurge",
                    "budget_category_id": venue_cat_id,
                    "estimated_amount": "400000.00",
                    "actual_amount": "450000.00",
                    "payment_status": "Paid",
                },
            )
            assert exp3_res.status_code == 201
            exp3_id = exp3_res.json()["id"]

            ev_detail3 = fresh_client.get(f"/api/events/{event_id}").json()
            b_sum3 = ev_detail3["budget_summary"]
            assert b_sum3["total_actual"] == "565000.00"
            assert b_sum3["over_budget"] is True
            assert b_sum3["utilization_percent"] == 113.0

            # Delete Expense 3 to return within budget
            del_exp3 = fresh_client.delete(f"/api/expenses/{exp3_id}")
            assert del_exp3.status_code == 204

            ev_detail4 = fresh_client.get(f"/api/events/{event_id}").json()
            assert ev_detail4["budget_summary"]["over_budget"] is False
            assert ev_detail4["budget_summary"]["total_actual"] == "115000.00"

            # -------------------------------------------------------------
            # STEP 6: Tasks: progress percentage and overdue flags
            # -------------------------------------------------------------
            # Add an overdue task (due date in past: 2026-10-25 < frozen today 2026-10-31)
            t_overdue_res = fresh_client.post(
                f"/api/events/{event_id}/tasks",
                json={
                    "title": "Send Save the Date Cards",
                    "category": "Invitations",
                    "priority": "High",
                    "due_date": "2026-10-25",
                },
            )
            assert t_overdue_res.status_code == 201
            overdue_task_id = t_overdue_res.json()["id"]
            assert t_overdue_res.json()["is_overdue"] is True

            # Check task summary: total=3, completed=0, progress=0%, overdue=1
            ev_tasks1 = fresh_client.get(f"/api/events/{event_id}").json()
            t_sum1 = ev_tasks1["task_summary"]
            assert t_sum1["total"] == 3
            assert t_sum1["completed"] == 0
            assert t_sum1["progress_percent"] == 0.0
            assert t_sum1["overdue"] >= 1

            # Mark overdue task as Completed
            t_complete_res = fresh_client.put(
                f"/api/tasks/{overdue_task_id}",
                json={"status": "Completed"},
            )
            assert t_complete_res.status_code == 200
            assert t_complete_res.json()["status"] == "Completed"
            assert t_complete_res.json()["is_overdue"] is False  # completed tasks are never overdue

            # Check updated task summary: progress should now be 33.3%
            ev_tasks2 = fresh_client.get(f"/api/events/{event_id}").json()
            t_sum2 = ev_tasks2["task_summary"]
            assert t_sum2["completed"] == 1
            assert t_sum2["progress_percent"] == 33.3

            # -------------------------------------------------------------
            # STEP 7: Vendors: quotation comparison and selected total
            # -------------------------------------------------------------
            # Vendor 1: Decoration (Considering - 95,000)
            v1_res = fresh_client.post(
                f"/api/events/{event_id}/vendors",
                json={
                    "name": "Marwar Decors",
                    "category": "Decoration",
                    "quoted_amount": "95000.00",
                    "status": "Considering",
                },
            )
            assert v1_res.status_code == 201
            v1_id = v1_res.json()["id"]

            # Vendor 2: Decoration (Selected - 105,000)
            v2_res = fresh_client.post(
                f"/api/events/{event_id}/vendors",
                json={
                    "name": "Royal Floral Designers",
                    "category": "Decoration",
                    "quoted_amount": "105000.00",
                    "status": "Selected",
                },
            )
            assert v2_res.status_code == 201
            v2_id = v2_res.json()["id"]

            # Vendor 3: Catering (Contacted - 140,000)
            v3_res = fresh_client.post(
                f"/api/events/{event_id}/vendors",
                json={
                    "name": "Lakeview Catering",
                    "category": "Catering",
                    "quoted_amount": "140000.00",
                    "status": "Contacted",
                },
            )
            assert v3_res.status_code == 201
            v3_id = v3_res.json()["id"]

            # Check vendor comparison
            comp_res = fresh_client.get(f"/api/events/{event_id}/vendors/comparison")
            assert comp_res.status_code == 200
            comp_data = comp_res.json()
            assert comp_data["selected_total"] == "105000.00"
            decor_comp = next(c for c in comp_data["categories"] if c["category"] == "Decoration")
            assert len(decor_comp["vendors"]) == 2
            assert decor_comp["lowest_quote"] == "95000.00"
            assert decor_comp["selected_vendors"] == ["Royal Floral Designers"]

            # Update Vendor 1 to Rejected
            v1_upd = fresh_client.put(f"/api/vendors/{v1_id}", json={"status": "Rejected"})
            assert v1_upd.status_code == 200
            assert v1_upd.json()["status"] == "Rejected"

            # Delete Vendor 3
            v3_del = fresh_client.delete(f"/api/vendors/{v3_id}")
            assert v3_del.status_code == 204

            # Verify only 2 vendors remain
            v_list = fresh_client.get(f"/api/events/{event_id}/vendors").json()
            assert len(v_list) == 2

            # -------------------------------------------------------------
            # STEP 8: Ask assistant in Ask mode; assert database row counts unchanged
            # -------------------------------------------------------------
            with FreshSession() as db:
                counts_before = {
                    "events": db.query(Event).count(),
                    "categories": db.query(BudgetCategory).count(),
                    "expenses": db.query(Expense).count(),
                    "tasks": db.query(Task).count(),
                    "vendors": db.query(Vendor).count(),
                    "proposals": db.query(ChangeProposal).count(),
                }

            mock_ask_resp = {
                "reply": "You can optimize your budget by sourcing local marigolds and negotiating buffet packages.",
                "recommendations": [
                    {"title": "Bulk Florals", "detail": "Source directly from local vendors"}
                ],
                "suggested_modification_prompts": [
                    "Can we move budget from Venue to Decoration?",
                    "What are typical florist rates?",
                ],
            }
            mock_ask_obj = MagicMock()
            mock_ask_obj.text = json.dumps(mock_ask_resp)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_ask_obj

                    ask_res = fresh_client.post(
                        f"/api/events/{event_id}/assistant",
                        json={"message": "How can I optimize our decoration costs?"},
                    )
                    assert ask_res.status_code == 200
                    assert "optimize your budget" in ask_res.json()["reply"]
                    assert len(ask_res.json()["suggested_modification_prompts"]) == 2

            with FreshSession() as db:
                counts_after = {
                    "events": db.query(Event).count(),
                    "categories": db.query(BudgetCategory).count(),
                    "expenses": db.query(Expense).count(),
                    "tasks": db.query(Task).count(),
                    "vendors": db.query(Vendor).count(),
                    "proposals": db.query(ChangeProposal).count(),
                }
            assert counts_before == counts_after, "Ask mode must never mutate any database tables"

            # -------------------------------------------------------------
            # STEP 9: Propose changes in Modify mode; verify preview; confirm and apply
            # -------------------------------------------------------------
            # Shift 20,000 from Venue (150,000 -> 130,000) to Decoration (75,000 -> 95,000)
            mock_proposal_resp = {
                "summary": "Transfer 20,000 INR from Venue to Decoration for grander entrance decor.",
                "new_total_budget": None,
                "budget_adjustments": [
                    {"category_name": "Venue", "delta_amount": "-20000.00"},
                    {"category_name": "Decoration", "delta_amount": "+20000.00"},
                ],
                "tasks_to_add": [
                    {
                        "title": "Review Floral Entrance Layout",
                        "category": "Decoration",
                        "priority": "High",
                        "due_date": "2026-11-08",
                        "description": "Approve final floral mockups",
                    }
                ],
                "tasks_to_update": [],
            }
            mock_prop_obj = MagicMock()
            mock_prop_obj.text = json.dumps(mock_proposal_resp)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_prop_obj

                    prop_res = fresh_client.post(
                        f"/api/events/{event_id}/assistant/propose-changes",
                        json={"message": "Shift 20,000 INR from Venue to Decoration and add a floral review task"},
                    )
                    assert prop_res.status_code == 200
                    prop_data = prop_res.json()
                    assert prop_data["proposal"] is not None
                    proposal_id = prop_data["proposal"]["proposal_id"]
                    assert proposal_id is not None
                    assert prop_data["proposal"]["preview"]["budget"]["balanced"] is True

            # Snapshot invariant tables before applying
            with FreshSession() as db:
                ev_before = db.get(Event, event_id)
                venue_amount_before = next(c.estimated_amount for c in ev_before.budget_categories if c.category_name == "Venue")
                decor_amount_before = next(c.estimated_amount for c in ev_before.budget_categories if c.category_name == "Decoration")
                exp_snapshot_before = json.dumps([e.id for e in ev_before.expenses], sort_keys=True)
                vend_snapshot_before = json.dumps([v.id for v in ev_before.vendors], sort_keys=True)
                plan_snapshot_before = json.dumps(ev_before.generated_plan, sort_keys=True)

            # Apply with confirm=True
            apply_res = fresh_client.post(
                f"/api/events/{event_id}/assistant/apply-changes",
                json={"proposal_id": proposal_id, "confirm": True},
            )
            assert apply_res.status_code == 200
            assert apply_res.json()["status"] == "applied"

            with FreshSession() as db:
                ev_after = db.get(Event, event_id)
                # Verify categories updated in place
                cat_venue = next(c for c in ev_after.budget_categories if c.category_name == "Venue")
                cat_decor = next(c for c in ev_after.budget_categories if c.category_name == "Decoration")
                assert cat_venue.estimated_amount == venue_amount_before - 2000000  # -20,000 INR
                assert cat_decor.estimated_amount == decor_amount_before + 2000000  # +20,000 INR
                # Total remains balanced
                assert sum(c.estimated_amount for c in ev_after.budget_categories) == 50000000

                # Verify new task was created
                new_task = next((t for t in ev_after.tasks if t.title == "Review Floral Entrance Layout"), None)
                assert new_task is not None
                assert new_task.category == "Decoration"

                # Verify invariants: expenses, vendors, generated_plan completely unchanged
                assert json.dumps([e.id for e in ev_after.expenses], sort_keys=True) == exp_snapshot_before
                assert json.dumps([v.id for v in ev_after.vendors], sort_keys=True) == vend_snapshot_before
                assert json.dumps(ev_after.generated_plan, sort_keys=True) == plan_snapshot_before

            # Duplicate apply returns 409 Conflict
            second_apply = fresh_client.post(
                f"/api/events/{event_id}/assistant/apply-changes",
                json={"proposal_id": proposal_id, "confirm": True},
            )
            assert second_apply.status_code == 409
            assert "already applied" in second_apply.json()["detail"].lower()

            # -------------------------------------------------------------
            # STEP 10: Generate themes and bilingual invitations (English & Hindi)
            # -------------------------------------------------------------
            # Recommend Themes (Stateless)
            mock_theme_resp = {
                "themes": [
                    {
                        "name": "Marwar Sunset Glamour",
                        "description": "Rich amber, deep saffron and gold lanterns under starlit skies.",
                        "color_palette": [
                            {"name": "Deep Amber", "hex": "#78350F"},
                            {"name": "Warm Saffron", "hex": "#D97706"},
                            {"name": "Gold", "hex": "#FDE68A"},
                        ],
                        "decoration_ideas": ["Brass urlis with floating flowers", "Marigold curtains"],
                        "lighting": "Fairy light canopies with warm vintage bulbs",
                        "venue_style": "Heritage courtyard",
                        "budget_share_percent": 20,
                        "implementation_tips": ["Rent brass urlis from local prop stores"],
                    },
                    {
                        "name": "Royal Emerald Court",
                        "description": "Emerald greens with ivory florals and heritage brass accents.",
                        "color_palette": [
                            {"name": "Emerald Green", "hex": "#065F46"},
                            {"name": "Ivory", "hex": "#FFFFF0"},
                            {"name": "Antique Gold", "hex": "#D4AF37"},
                        ],
                        "decoration_ideas": ["Mughal arch backdrops", "Velvet drapes"],
                        "lighting": "Warm ambient amber wash lighting",
                        "venue_style": "Royal banquet lawn",
                        "budget_share_percent": 25,
                        "implementation_tips": ["Use local velvet suppliers"],
                    },
                    {
                        "name": "Starlight Ivory Elegance",
                        "description": "Classic ivory, crystal chandeliers, and ethereal white orchids.",
                        "color_palette": [
                            {"name": "Pearl White", "hex": "#F8FAFC"},
                            {"name": "Soft Gold", "hex": "#FEF08A"},
                            {"name": "Champagne", "hex": "#F7E7CE"},
                        ],
                        "decoration_ideas": ["Crystal candelabras", "Cascading orchid arches"],
                        "lighting": "Cool white pin spots and starlight ceiling",
                        "venue_style": "Glasshouse pavilion",
                        "budget_share_percent": 22,
                        "implementation_tips": ["Opt for in-season white blooms"],
                    },
                ]
            }
            mock_theme_obj = MagicMock()
            mock_theme_obj.text = json.dumps(mock_theme_resp)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_theme_obj

                    theme_res = fresh_client.post(
                        "/api/themes/recommend",
                        json={
                            "event_type": "Wedding",
                            "location": "Udaipur",
                            "guest_count": 120,
                            "total_budget": "500000.00",
                            "currency": "INR",
                        },
                    )
                    assert theme_res.status_code == 200
                    assert len(theme_res.json()["themes"]) >= 1

            # Generate Bilingual Invitations: English
            mock_inv_en = {
                "invitation_text": "You are cordially invited to celebrate the grand Sangeet of Priya at Udaipur Palace on Friday, November 20, 2026 at 18:30.",
            }
            mock_inv_en_obj = MagicMock()
            mock_inv_en_obj.text = json.dumps(mock_inv_en)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_inv_en_obj

                    inv_en_res = fresh_client.post(
                        "/api/invitations/generate",
                        json={
                            "event_type": "Wedding",
                            "host_name": "Priya Sharma",
                            "event_date": "2026-11-20",
                            "event_time": "18:30",
                            "location": "Udaipur Palace",
                            "language": "English",
                            "tone": "Elegant",
                        },
                    )
                    assert inv_en_res.status_code == 200
                    assert "cordially invited" in inv_en_res.json()["invitation_text"]
                    assert inv_en_res.json()["language"] == "English"

            # Generate Bilingual Invitations: Hindi (Devanagari)
            mock_inv_hi = {
                "invitation_text": "सस्नेह नमस्कार। हमारे परिवार में प्रिया के संगीत समारोह का शुभ आयोजन उदयपुर पैलेस में होने जा रहा है। आप सपरिवार सादर आमंत्रित हैं।",
            }
            mock_inv_hi_obj = MagicMock()
            mock_inv_hi_obj.text = json.dumps(mock_inv_hi)

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                with patch("google.genai.Client.models") as mock_models:
                    mock_models.generate_content.return_value = mock_inv_hi_obj

                    inv_hi_res = fresh_client.post(
                        "/api/invitations/generate",
                        json={
                            "event_type": "Wedding",
                            "host_name": "प्रिया शर्मा",
                            "event_date": "2026-11-20",
                            "event_time": "18:30",
                            "location": "उदयपुर पैलेस",
                            "language": "Hindi",
                            "tone": "Traditional",
                        },
                    )
                    assert inv_hi_res.status_code == 200
                    assert inv_hi_res.json()["language"] == "Hindi"
                    assert "सस्नेह नमस्कार" in inv_hi_res.json()["invitation_text"]

            # -------------------------------------------------------------
            # STEP 11: Verify Gemini failure mapping (504, 429, 502, 500)
            # -------------------------------------------------------------
            # 504 Timeout
            def slow_gemini(*args, **kwargs):
                import time
                time.sleep(0.05)
                return MagicMock(text="{}")

            with patch("app.config.settings.gemini_api_key", "mock_key_e2e"):
                svc_timeout = AIService(api_key="mock_key", timeout_seconds=0.01)
                with patch.object(svc_timeout._client.models, "generate_content", side_effect=slow_gemini):
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        asyncio.run(
                            svc_timeout.generate_structured("sys", "usr", AIProposalResponse)
                        )
                    assert exc.value.status_code == 504
                    assert "timed out" in exc.value.detail.lower()

            # 429 Rate Limit / Quota
            rate_err = errors.APIError(429, "Resource has been exhausted (check quota)")
            svc_429 = AIService(api_key="mock_key")
            with patch.object(svc_429._client.models, "generate_content", side_effect=rate_err):
                with pytest.raises(HTTPException) as exc:
                    asyncio.run(svc_429.generate_structured("sys", "usr", AIProposalResponse))
                assert exc.value.status_code == 429
                assert "quota" in exc.value.detail.lower() or "rate limit" in exc.value.detail.lower()

            # 502 Unusable / malformed output
            empty_resp = MagicMock(text="")
            svc_502 = AIService(api_key="mock_key")
            with patch.object(svc_502._client.models, "generate_content", return_value=empty_resp):
                with pytest.raises(HTTPException) as exc:
                    asyncio.run(svc_502.generate_structured("sys", "usr", AIProposalResponse))
                assert exc.value.status_code == 502
                assert "unusable" in exc.value.detail.lower() or "empty" in exc.value.detail.lower()

            # 500 Unexpected generic error
            svc_500 = AIService(api_key="mock_key")
            with patch.object(svc_500._client.models, "generate_content", side_effect=RuntimeError("Unexpected crash")):
                with pytest.raises(HTTPException) as exc:
                    asyncio.run(svc_500.generate_structured("sys", "usr", AIProposalResponse))
                assert exc.value.status_code == 500

            # -------------------------------------------------------------
            # STEP 12: Verify demo mode labels and behavior without API key
            # -------------------------------------------------------------
            with patch("app.config.settings.gemini_api_key", ""):
                demo_res = fresh_client.post(
                    "/api/events/generate",
                    json={
                        "event_name": "Demo Community Gathering",
                        "event_type": "Community Event",
                        "event_date": "2026-11-25",
                        "location": "Delhi Town Hall",
                        "guest_count": 80,
                        "total_budget": 100000,
                        "currency": "INR",
                    },
                )
                assert demo_res.status_code == 200
                demo_data = demo_res.json()
                assert demo_data["source"] == "demo"
                assert any("Demo mode" in w for w in demo_data["warnings"])
                assert demo_data["budget"]["total_allocated"] == 100000

            # -------------------------------------------------------------
            # STEP 13: Delete event; cascading deletion while preserving other events
            # -------------------------------------------------------------
            # Create a second event (Event B) to verify it remains intact
            ev_b_res = fresh_client.post(
                "/api/events",
                json={
                    "name": "Second Independent Event B",
                    "event_type": "Birthday",
                    "event_date": "2026-12-01",
                    "location": "Mumbai",
                    "guest_count": 30,
                    "total_budget": "75000.00",
                    "currency": "INR",
                },
            )
            assert ev_b_res.status_code == 201
            event_b_id = ev_b_res.json()["id"]

            # Add a category and task to Event B
            with FreshSession() as db:
                db.add(BudgetCategory(event_id=event_b_id, category_name="Cake", estimated_amount=1500000))
                db.add(Task(event_id=event_b_id, title="Order Birthday Cake", category="Food", priority="High", due_date=date(2026, 11, 28)))
                db.commit()

            # Delete Event A
            del_a_res = fresh_client.delete(f"/api/events/{event_id}")
            assert del_a_res.status_code == 204

            # Verify Event A is 404
            assert fresh_client.get(f"/api/events/{event_id}").status_code == 404

            # Query database directly to assert cascading deletion of Event A's child records
            with FreshSession() as db:
                # Event A child rows must all be 0
                assert db.query(BudgetCategory).filter(BudgetCategory.event_id == event_id).count() == 0
                assert db.query(Expense).filter(Expense.event_id == event_id).count() == 0
                assert db.query(Task).filter(Task.event_id == event_id).count() == 0
                assert db.query(Vendor).filter(Vendor.event_id == event_id).count() == 0
                assert db.query(ChangeProposal).filter(ChangeProposal.event_id == event_id).count() == 0

                # Event B and its child records must still exist and be completely intact!
                ev_b_db = db.get(Event, event_b_id)
                assert ev_b_db is not None
                assert ev_b_db.name == "Second Independent Event B"
                assert len(ev_b_db.budget_categories) == 1
                assert ev_b_db.budget_categories[0].category_name == "Cake"
                assert len(ev_b_db.tasks) == 1
                assert ev_b_db.tasks[0].title == "Order Birthday Cake"

    finally:
        app.dependency_overrides.pop(get_db, None)
        set_frozen_today(None)
        set_frozen_now(None)
        ai_rate_limiter.reset()
        engine.dispose()
        if "fresh_engine" in locals():
            fresh_engine.dispose()
