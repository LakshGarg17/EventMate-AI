import os
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath("backend"))

from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup temp database path
TEMP_DB_PATH = os.path.abspath("temp_e2e_day3.db")
if os.path.exists(TEMP_DB_PATH):
    try:
        os.remove(TEMP_DB_PATH)
    except OSError:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB_PATH}"

from app.db.database import Base, get_db
from app.db import models
from app.main import app

def run_verification():
    print("=" * 60)
    print("EVENTMATE AI: DAY 3 E2E VERIFICATION SUITE")
    print("=" * 60)

    # 1. Initialize Tables
    print("\n[Step 1] Initializing fresh SQLite schema...")
    engine = create_engine(f"sqlite:///{TEMP_DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    print("-> Schema initialized successfully.")

    # 2. Create Event with Day 1 Plan
    print("\n[Step 2] Generating Day 1 Plan and creating event...")
    plan_req = {
        "event_name": "E2E Royal Gala",
        "event_type": "Wedding",
        "guest_count": 250,
        "location": "Udaipur",
        "total_budget": "1000000.00",
        "currency": "INR",
        "event_date": "2026-11-20",
        "preferences": "Royal Rajasthani Heritage, vegetarian fine dining, folk music"
    }
    plan_res = client.post("/api/events/generate", json=plan_req)
    assert plan_res.status_code == 200, f"Generate plan failed: {plan_res.text}"
    generated_plan = plan_res.json()
    print(f"-> Generated Day 1 Plan (Source: {generated_plan.get('source')}, Model: {generated_plan.get('model')})")

    event_payload = {
        "name": "E2E Royal Gala",
        "event_type": "Wedding",
        "event_date": "2026-11-20",
        "location": "Udaipur",
        "guest_count": 250,
        "total_budget": "1000000.00",
        "currency": "INR",
        "preferred_theme": "Royal Rajasthani Heritage",
        "additional_preferences": "Vegetarian fine dining, folk music",
        "generated_plan": generated_plan
    }
    res = client.post("/api/events", json=event_payload)
    assert res.status_code == 201, f"Create event failed: {res.text}"
    event_data = res.json()
    event_id = event_data["id"]
    print(f"-> Created Event ID: {event_id}")
    print(f"   Name: {event_data['name']}, Budget: INR {event_data['total_budget']}")
    print(f"   Categories created: {len(event_data.get('budget_categories', []))}")
    print(f"   Tasks created: {len(event_data.get('tasks', []))}")
    assert len(event_data.get('budget_categories', [])) > 0
    assert len(event_data.get('tasks', [])) > 0

    # 3. Ask Mode Query
    print("\n[Step 3] Testing Assistant Ask Mode...")
    assistant_payload = {
        "message": "What should I focus on next, and how can I save ₹50,000?"
    }
    res = client.post(f"/api/events/{event_id}/assistant", json=assistant_payload)
    assert res.status_code == 200, f"Assistant ask failed: {res.text}"
    ask_data = res.json()
    print(f"-> Reply Source: {ask_data['source']}")
    print(f"   Changes Applied: {ask_data['changes_applied']}")
    print(f"   Reply excerpt: {ask_data['reply'][:120]}...")
    print(f"   Suggested modification prompts: {ask_data.get('suggested_modification_prompts')}")
    assert ask_data["changes_applied"] is False

    # 4. Propose & Apply Changes (Mocked AI response for Modify Mode)
    print("\n[Step 4] Testing Plan Modification (Propose, Preview, Apply)...")
    from unittest.mock import patch, AsyncMock
    from app.schemas import AIProposalResponse, BudgetAdjustment, TaskToAdd
    from app.services.ai_service import AIService
    from app.config import settings

    mock_proposal = AIProposalResponse(
        summary="Reallocated 50,000 from Decoration to Catering and added final food tasting milestone.",
        new_total_budget=None,
        budget_adjustments=[
            BudgetAdjustment(category_name="Decoration", delta_amount="-50000.00"),
            BudgetAdjustment(category_name="Catering", delta_amount="50000.00"),
        ],
        tasks_to_add=[
            TaskToAdd(
                title="Final Menu Tasting with Chef",
                description="Approve starters and traditional sweets",
                category="Catering",
                priority="High",
                due_date="2026-11-10"
            )
        ],
        tasks_to_update=[],
        clarification_question=None
    )

    with patch.object(settings, "gemini_api_key", "fake_key_for_mock_test"):
        with patch.object(AIService, "generate_structured", new=AsyncMock(return_value=(mock_proposal, "gemini", "gemini-2.5-flash"))):
            prop_res = client.post(f"/api/events/{event_id}/assistant/propose-changes", json={"message": "Move 50k from decor to catering and add tasting"})
            assert prop_res.status_code == 200, f"Propose changes failed: {prop_res.text}"
        prop_data = prop_res.json()
        proposal_id = prop_data["proposal"]["proposal_id"]
        print(f"-> Created Proposal ID: {proposal_id}")
        print(f"   Summary: {prop_data['proposal']['summary']}")
        print(f"   Budget preview categories: {len(prop_data['proposal']['preview']['budget']['categories'])}")
        print(f"   Tasks to add preview: {len(prop_data['proposal']['preview']['tasks_to_add'])}")

        # Apply Proposal
        apply_res = client.post(
            f"/api/events/{event_id}/assistant/apply-changes",
            json={"proposal_id": proposal_id, "confirm": True}
        )
        assert apply_res.status_code == 200, f"Apply changes failed: {apply_res.text}"
        apply_data = apply_res.json()
        print(f"-> Successfully applied proposal!")
        print(f"   Status: {apply_data['status']}")
        print(f"   Updated event categories: {len(apply_data['categories'])}")
        print(f"   Updated event tasks: {len(apply_data['tasks'])}")

    # 5. Themes Recommendation
    print("\n[Step 5] Testing Theme & Creative Recommendation...")
    theme_payload = {
        "event_type": "Wedding",
        "guest_count": 250,
        "location": "Udaipur",
        "total_budget": "1000000.00",
        "currency": "INR",
        "preferred_style": "Heritage Royal"
    }
    theme_res = client.post("/api/themes/recommend", json=theme_payload)
    assert theme_res.status_code == 200, f"Themes failed: {theme_res.text}"
    theme_data = theme_res.json()
    print(f"-> Themes generated ({theme_data['source']}): {len(theme_data['themes'])} themes")
    for t in theme_data["themes"]:
        hex_colors = [c['hex'] for c in t['color_palette']]
        print(f"   - {t['name']}: {t['estimated_decoration_budget']} decor budget, colors: {hex_colors}")

    # 6. Invitations in English and Hindi
    print("\n[Step 6] Testing Invitation Generator (English & Hindi)...")
    inv_en_payload = {
        "event_type": "Wedding",
        "host_name": "Sharma & Verma Families",
        "event_date": "2026-11-20",
        "event_time": "18:00",
        "location": "Lake Palace, Udaipur",
        "language": "English",
        "tone": "Formal"
    }
    inv_en_res = client.post("/api/invitations/generate", json=inv_en_payload)
    assert inv_en_res.status_code == 200, f"English invitation failed: {inv_en_res.text}"
    print(f"-> English invitation ({inv_en_res.json()['source']}):")
    print(f"   Excerpt: {inv_en_res.json()['invitation_text'][:100]}...")

    inv_hi_payload = {
        "event_type": "Wedding",
        "host_name": "शर्मा एवं वर्मा परिवार",
        "event_date": "2026-11-20",
        "event_time": "18:00",
        "location": "झील महल, उदयपुर",
        "language": "Hindi",
        "tone": "Formal"
    }
    inv_hi_res = client.post("/api/invitations/generate", json=inv_hi_payload)
    assert inv_hi_res.status_code == 200, f"Hindi invitation failed: {inv_hi_res.text}"
    hi_content = inv_hi_res.json()["invitation_text"]
    print(f"-> Hindi invitation ({inv_hi_res.json()['source']}):")
    print(f"   Excerpt: {hi_content[:100]}...")

    # Check Devanagari ratio
    devanagari_chars = sum(1 for c in hi_content if 0x0900 <= ord(c) <= 0x097F)
    letters = sum(1 for c in hi_content if c.isalnum())
    ratio = devanagari_chars / max(1, letters)
    print(f"   Devanagari script ratio: {ratio:.2%}")
    assert ratio >= 0.30, f"Expected Devanagari ratio >= 0.30, got {ratio}"

    # 7. Vendors & Quotation Comparison
    print("\n[Step 7] Testing Vendor Management & Quotation Comparison...")
    # Vendor 1: Royal Palace (higher quote)
    v1_res = client.post(f"/api/events/{event_id}/vendors", json={
        "name": "Royal Palace Venue",
        "category": "Venue",
        "status": "Considering",
        "quoted_amount": "350000.00",
        "notes": "[★ 5] Includes banquet hall and lawn"
    })
    assert v1_res.status_code == 201, f"Create vendor 1 failed: {v1_res.text}"
    v1_id = v1_res.json()["id"]

    # Vendor 2: Heritage Court (lowest quote)
    v2_res = client.post(f"/api/events/{event_id}/vendors", json={
        "name": "Heritage Court Venue",
        "category": "Venue",
        "status": "Considering",
        "quoted_amount": "280000.00",
        "notes": "[★ 4] Lawn only"
    })
    assert v2_res.status_code == 201, f"Create vendor 2 failed: {v2_res.text}"
    v2_id = v2_res.json()["id"]

    # Comparison 1: No vendor selected yet
    comp1 = client.get(f"/api/events/{event_id}/vendors/comparison").json()
    print(f"-> Comparison 1: Total comparison categories: {len(comp1['categories'])}")
    venue_comp = next(c for c in comp1["categories"] if c["category"] == "Venue")
    print(f"   Lowest quote: INR {venue_comp['lowest_quote']} (Vendor ID: {venue_comp['lowest_vendor_ids']})")
    assert venue_comp["lowest_quote"] == "280000.00"
    assert v2_id in venue_comp["lowest_vendor_ids"]
    assert len(venue_comp["selected_vendors"]) == 0

    # Select Vendor 1 (Royal Palace Venue)
    update_res = client.put(f"/api/vendors/{v1_id}", json={"status": "Selected"})
    assert update_res.status_code == 200, f"Update vendor failed: {update_res.text}"

    # Comparison 2: Selected vendor difference
    comp2 = client.get(f"/api/events/{event_id}/vendors/comparison").json()
    venue_comp2 = next(c for c in comp2["categories"] if c["category"] == "Venue")
    print(f"-> Comparison 2: Selected vendors: {venue_comp2['selected_vendors']}")
    sel_vendor_item = next(v for v in venue_comp2["vendors"] if v["id"] == v1_id)
    print(f"   Selected quote: INR {sel_vendor_item['quoted_amount']}")
    print(f"   Difference from lowest: INR {sel_vendor_item['difference_from_lowest']}")
    print(f"   Selected Total across event: INR {comp2['selected_total']}")
    assert venue_comp2["selected_vendors"] == ["Royal Palace Venue"]
    assert sel_vendor_item["quoted_amount"] == "350000.00"
    assert sel_vendor_item["difference_from_lowest"] == "70000.00"
    assert comp2["selected_total"] == "350000.00"

    # 8. Persistence check: dispose engine and reconnect fresh
    print("\n[Step 8] Testing SQLite persistence across process restart...")
    engine.dispose()

    # Reconnect fresh engine
    restarted_engine = create_engine(f"sqlite:///{TEMP_DB_PATH}", connect_args={"check_same_thread": False})
    RestartedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=restarted_engine)

    def override_restarted_db():
        db = RestartedSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_restarted_db

    restarted_client = TestClient(app)
    reloaded_event = restarted_client.get(f"/api/events/{event_id}").json()
    reloaded_vendors = restarted_client.get(f"/api/events/{event_id}/vendors").json()

    print(f"-> Successfully read event after restart: {reloaded_event['name']}")
    print(f"   Vendors restored: {len(reloaded_vendors)}")
    assert len(reloaded_vendors) == 2
    assert any(v["status"] == "Selected" for v in reloaded_vendors)

    # 9. CORS Check
    print("\n[Step 9] Testing CORS preflight and headers...")
    cors_res = restarted_client.options(
        "/api/events",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    print(f"-> CORS OPTIONS Status: {cors_res.status_code}")
    print(f"   Access-Control-Allow-Origin: {cors_res.headers.get('access-control-allow-origin')}")
    assert cors_res.status_code == 200
    assert cors_res.headers.get("access-control-allow-origin") == "http://localhost:5173"

    print("\n" + "=" * 60)
    print("ALL E2E VERIFICATIONS PASSED CLEANLY!")
    print("=" * 60)

    # Cleanup temp db
    restarted_engine.dispose()
    try:
        os.remove(TEMP_DB_PATH)
        print(f"Cleaned up temporary test database: {TEMP_DB_PATH}")
    except OSError:
        pass

if __name__ == "__main__":
    run_verification()
