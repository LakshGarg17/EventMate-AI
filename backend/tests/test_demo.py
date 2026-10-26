from datetime import date, timedelta
from app.schemas import EventRequest
from app.services.demo import generate_demo_plan


def test_demo_plan_generation_and_warning():
    event_date = date.today() + timedelta(days=30)
    req = EventRequest(
        event_name="Rohit & Priya Wedding",
        event_type="Wedding",
        event_date=event_date,
        location="Jaipur, Rajasthan",
        guest_count=350,
        total_budget=1500000,
        currency="INR",
        theme="Royal Rajasthani",
        additional_preferences="Vegetarian catering only"
    )

    plan = generate_demo_plan(req)

    assert plan.source == "demo"
    assert plan.model is None
    assert any("Demo mode: generated without an AI model" in w for w in plan.warnings)
    assert plan.event_details.event_name == "Rohit & Priya Wedding"
    assert plan.budget.total_allocated == 1500000
    assert sum(item.amount for item in plan.budget.items) == 1500000
    assert len(plan.timeline) > 0
    assert len(plan.checklist) > 0
    assert len(plan.decoration_suggestions) > 0
    assert len(plan.catering_suggestions) > 0
    assert len(plan.entertainment_suggestions) > 0
    assert len(plan.vendor_requirements) > 0
    assert len(plan.risks) > 0
