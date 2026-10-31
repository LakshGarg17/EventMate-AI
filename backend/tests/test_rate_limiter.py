from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.services.rate_limiter import ai_rate_limiter


def test_ai_rate_limiter_under_limit(client):
    """Requests under the limit succeed."""
    ai_rate_limiter.reset()
    with patch.object(settings, "ai_rate_limit_per_minute", 5):
        for i in range(5):
            res = client.post(
                "/api/themes/recommend",
                json={
                    "event_type": "Birthday",
                    "total_budget": "50000.00",
                    "currency": "INR",
                    "guest_count": 50,
                    "location": "Mumbai",
                },
            )
            assert res.status_code == 200


def test_ai_rate_limiter_over_limit_triggers_429(client):
    """Requests exceeding the limit return 429 with Retry-After header."""
    ai_rate_limiter.reset()
    fake_time = 1000.0
    ai_rate_limiter.clock = lambda: fake_time

    with patch.object(settings, "ai_rate_limit_per_minute", 2):
        # Request 1 & 2 succeed
        res1 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res1.status_code == 200

        res2 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res2.status_code == 200

        # Request 3 triggers 429
        res3 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res3.status_code == 429
        assert "Retry-After" in res3.headers
        assert "Too many AI requests" in res3.json()["detail"]


def test_ai_rate_limiter_window_reset(client):
    """Advancing clock beyond sliding window allows new requests."""
    ai_rate_limiter.reset()
    current_time = [1000.0]
    ai_rate_limiter.clock = lambda: current_time[0]

    with patch.object(settings, "ai_rate_limit_per_minute", 1):
        res1 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res1.status_code == 200

        # Immediate second request blocked
        res2 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res2.status_code == 429

        # Advance clock by 61 seconds
        current_time[0] += 61.0
        res3 = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Birthday",
                "total_budget": "50000.00",
                "currency": "INR",
                "guest_count": 50,
                "location": "Mumbai",
            },
        )
        assert res3.status_code == 200


def test_ai_rate_limiter_disabled_when_zero(client):
    """Setting limit to 0 disables rate limiting."""
    ai_rate_limiter.reset()
    with patch.object(settings, "ai_rate_limit_per_minute", 0):
        for _ in range(12):
            res = client.post(
                "/api/themes/recommend",
                json={
                    "event_type": "Birthday",
                    "total_budget": "50000.00",
                    "currency": "INR",
                    "guest_count": 50,
                    "location": "Mumbai",
                },
            )
            assert res.status_code == 200


def test_non_ai_endpoints_never_rate_limited(client):
    """Health checks and CRUD operations are exempt from AI rate limiting."""
    ai_rate_limiter.reset()
    with patch.object(settings, "ai_rate_limit_per_minute", 1):
        for _ in range(5):
            res = client.get("/health")
            assert res.status_code == 200
            res_ready = client.get("/health/ready")
            assert res_ready.status_code == 200
            res_events = client.get("/api/events")
            assert res_events.status_code == 200


def test_trust_proxy_headers(client):
    """X-Forwarded-For header is used when trust_proxy_headers is enabled."""
    ai_rate_limiter.reset()
    with patch.object(settings, "ai_rate_limit_per_minute", 1):
        with patch.object(settings, "trust_proxy_headers", True):
            # Client A
            res_a = client.post(
                "/api/themes/recommend",
                headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18"},
                json={
                    "event_type": "Birthday",
                    "total_budget": "50000.00",
                    "currency": "INR",
                    "guest_count": 50,
                    "location": "Mumbai",
                },
            )
            assert res_a.status_code == 200

            # Client B from different IP succeeds even though A hit limit
            res_b = client.post(
                "/api/themes/recommend",
                headers={"X-Forwarded-For": "198.51.100.4"},
                json={
                    "event_type": "Birthday",
                    "total_budget": "50000.00",
                    "currency": "INR",
                    "guest_count": 50,
                    "location": "Mumbai",
                },
            )
            assert res_b.status_code == 200

