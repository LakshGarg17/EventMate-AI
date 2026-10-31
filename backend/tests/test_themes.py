from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from google.genai import errors

from app.db.models import Event
from app.services.ai_service import AIService


def test_themes_demo_mode(client):
    with patch("app.config.settings.gemini_api_key", ""):
        res = client.post(
            "/api/themes/recommend",
            json={
                "event_type": "Wedding",
                "total_budget": "500000.00",
                "currency": "INR",
                "guest_count": 150,
                "location": "Jaipur",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["source"] == "demo"
        assert len(data["themes"]) == 3
        for theme in data["themes"]:
            assert 5 <= theme["budget_share_percent"] <= 40
            assert theme["is_estimate"] is True
            assert len(theme["color_palette"]) >= 3
            for c in theme["color_palette"]:
                assert c["hex"].startswith("#")
                assert len(c["hex"]) == 7


def test_themes_validation_errors(client):
    # Invalid event_type
    res = client.post(
        "/api/themes/recommend",
        json={
            "event_type": "InvalidType",
            "total_budget": "500000.00",
            "guest_count": 100,
            "location": "Delhi",
        },
    )
    assert res.status_code == 422

    # Non-positive budget
    res = client.post(
        "/api/themes/recommend",
        json={
            "event_type": "Wedding",
            "total_budget": "0",
            "guest_count": 100,
            "location": "Delhi",
        },
    )
    assert res.status_code == 422

    # Zero guest count
    res = client.post(
        "/api/themes/recommend",
        json={
            "event_type": "Wedding",
            "total_budget": "500000",
            "guest_count": 0,
            "location": "Delhi",
        },
    )
    assert res.status_code == 422

    # Missing location
    res = client.post(
        "/api/themes/recommend",
        json={
            "event_type": "Wedding",
            "total_budget": "500000",
            "guest_count": 100,
            "location": "   ",
        },
    )
    assert res.status_code == 422


def test_themes_unknown_event_id_404(client):
    res = client.post(
        "/api/themes/recommend",
        json={
            "event_type": "Wedding",
            "total_budget": "500000",
            "guest_count": 100,
            "location": "Delhi",
            "event_id": "nonexistent-event-id-9999",
        },
    )
    assert res.status_code == 404
    assert "event_id not found" in res.json()["detail"].lower()


def test_themes_mocked_gemini_call_and_sanitization(client):
    mock_json = """
    {
        "themes": [
            {
                "name": "Theme 1",
                "description": "Desc 1",
                "color_palette": [{"name": "Gold", "hex": "#ffd700"}, {"name": "Red", "hex": "#ff0000"}, {"name": "White", "hex": "#ffffff"}],
                "decoration_ideas": ["Decor 1"],
                "lighting": "Light 1",
                "venue_style": "Style 1",
                "budget_share_percent": 15,
                "implementation_tips": ["Tip 1"]
            },
            {
                "name": "Theme 2",
                "description": "Desc 2",
                "color_palette": [{"name": "Pink", "hex": "#ffc0cb"}, {"name": "BadHex", "hex": "not-a-hex"}, {"name": "Blue", "hex": "#0000ff"}, {"name": "Green", "hex": "#008000"}],
                "decoration_ideas": ["Decor 2"],
                "lighting": "Light 2",
                "venue_style": "Style 2",
                "budget_share_percent": 25,
                "implementation_tips": ["Tip 2"]
            },
            {
                "name": "Theme 3",
                "description": "Desc 3",
                "color_palette": [{"name": "Silver", "hex": "#c0c0c0"}, {"name": "Black", "hex": "#000000"}, {"name": "Ivory", "hex": "#fffff0"}],
                "decoration_ideas": ["Decor 3"],
                "lighting": "Light 3",
                "venue_style": "Style 3",
                "budget_share_percent": 50,
                "implementation_tips": ["Tip 3"]
            },
            {
                "name": "theme 1",
                "description": "Duplicate name should be dropped",
                "color_palette": [{"name": "A", "hex": "#111111"}, {"name": "B", "hex": "#222222"}, {"name": "C", "hex": "#333333"}],
                "decoration_ideas": ["Decor"],
                "lighting": "Light",
                "venue_style": "Style",
                "budget_share_percent": 20,
                "implementation_tips": ["Tip"]
            }
        ]
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_json

    with patch("app.config.settings.gemini_api_key", "test_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                res = client.post(
                    "/api/themes/recommend",
                    json={
                        "event_type": "Wedding",
                        "total_budget": "100000.00",
                        "currency": "INR",
                        "guest_count": 100,
                        "location": "Jaipur",
                    },
                )
                assert res.status_code == 200
                data = res.json()
                assert data["source"] == "gemini"
                themes = data["themes"]

                # Exactly 3 themes: duplicate "theme 1" dropped!
                assert len(themes) == 3

                # Hex normalized to uppercase
                assert themes[0]["color_palette"][0]["hex"] == "#FFD700"

                # Bad hex dropped from Theme 2, but 3 valid remain
                assert all(c["name"] != "BadHex" for c in themes[1]["color_palette"])
                assert len(themes[1]["color_palette"]) == 3

                # Budget share clamped: Theme 3 had 50%, should clamp to 40%
                assert themes[2]["budget_share_percent"] == 40
                assert themes[2]["estimated_decoration_budget"] == "40000.00"


def test_themes_fewer_than_3_triggers_retry_then_502(client):
    mock_too_few = MagicMock(text='{"themes": [{"name": "Only One", "description": "d", "color_palette": [{"name": "A", "hex": "#FFFFFF"}, {"name": "B", "hex": "#000000"}, {"name": "C", "hex": "#123456"}], "decoration_ideas": ["idea"], "lighting": "light", "venue_style": "style", "budget_share_percent": 10, "implementation_tips": ["tip"]}]}')

    with patch("app.config.settings.gemini_api_key", "test_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_too_few
                mock_client_cls.return_value = mock_client

                res = client.post(
                    "/api/themes/recommend",
                    json={
                        "event_type": "Birthday",
                        "total_budget": "50000",
                        "guest_count": 30,
                        "location": "Goa",
                    },
                )
                assert res.status_code == 502
                assert "fewer than 3" in res.json()["detail"].lower()

