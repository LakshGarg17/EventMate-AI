from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_event_plan_valid_demo():
    event_date = (date.today() + timedelta(days=20)).isoformat()
    payload = {
        "event_name": "Community Art Fest",
        "event_type": "Community Event",
        "event_date": event_date,
        "location": "Central Community Center",
        "guest_count": 150,
        "total_budget": 100000,
        "currency": "INR",
        "theme": "Local Artisan Colors",
        "additional_preferences": "Wheelchair accessible"
    }

    response = client.post("/api/events/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["source"] in ("demo", "gemini")
    assert "id" in data
    assert "generated_at" in data
    assert data["event_details"]["event_name"] == "Community Art Fest"
    assert data["budget"]["total_allocated"] == 100000
    assert sum(item["amount"] for item in data["budget"]["items"]) == 100000
    assert len(data["timeline"]) > 0
    assert len(data["checklist"]) > 0
    assert len(data["risks"]) > 0
    assert isinstance(data["warnings"], list)


def test_generate_event_plan_missing_fields_returns_422():
    payload = {
        "event_name": "Incomplete Event"
    }
    response = client.post("/api/events/generate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "errors" in data or "detail" in data


def test_generate_event_plan_zero_guest_returns_422():
    event_date = (date.today() + timedelta(days=10)).isoformat()
    payload = {
        "event_name": "Bad Guest Count",
        "event_type": "Birthday",
        "event_date": event_date,
        "location": "Park",
        "guest_count": 0,
        "total_budget": 50000,
    }
    response = client.post("/api/events/generate", json=payload)
    assert response.status_code == 422


def test_generate_event_plan_negative_budget_returns_422():
    event_date = (date.today() + timedelta(days=10)).isoformat()
    payload = {
        "event_name": "Negative Budget",
        "event_type": "Birthday",
        "event_date": event_date,
        "location": "Park",
        "guest_count": 10,
        "total_budget": -500,
    }
    response = client.post("/api/events/generate", json=payload)
    assert response.status_code == 422


def test_generate_event_plan_past_date_returns_422():
    past_date = (date.today() - timedelta(days=5)).isoformat()
    payload = {
        "event_name": "Past Event",
        "event_type": "Wedding",
        "event_date": past_date,
        "location": "Hall",
        "guest_count": 50,
        "total_budget": 50000,
    }
    response = client.post("/api/events/generate", json=payload)
    assert response.status_code == 422


def test_cors_preflight():
    response = client.options(
        "/api/events/generate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
