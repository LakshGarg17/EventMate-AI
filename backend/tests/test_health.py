import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ai_configured" in data
    assert isinstance(data["ai_configured"], bool)
    # Ensure no secret keys are exposed
    assert "api_key" not in data
    assert "key" not in data


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ai_configured" in data


def test_health_ready_endpoints():
    # Root /health/ready
    res1 = client.get("/health/ready")
    assert res1.status_code == 200
    assert res1.json() == {"status": "ok", "database": "ok"}

    # Sub-path /api/health/ready
    res2 = client.get("/api/health/ready")
    assert res2.status_code == 200
    assert res2.json() == {"status": "ok", "database": "ok"}
