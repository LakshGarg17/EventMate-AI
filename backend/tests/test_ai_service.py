import asyncio
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from google.genai import errors

from app.schemas import EventRequest
from app.services.ai_service import AIService, clean_json_text


@pytest.fixture
def sample_request():
    return EventRequest(
        event_name="Silver Jubilee Anniversary",
        event_type="Wedding",
        event_date=date.today() + timedelta(days=45),
        location="Bengaluru",
        guest_count=100,
        total_budget=500000,
        currency="INR",
    )


def test_clean_json_text():
    raw_markdown = "```json\n{\"overview\": \"Great party\"}\n```"
    assert clean_json_text(raw_markdown) == "{\"overview\": \"Great party\"}"
    plain = "{\"overview\": \"Great party\"}"
    assert clean_json_text(plain) == plain


@pytest.mark.asyncio
async def test_ai_service_demo_fallback_when_no_key(sample_request):
    service = AIService(api_key="")
    assert not service.is_configured
    plan = await service.generate_plan(sample_request)
    assert plan.source == "demo"
    assert any("Demo mode" in w for w in plan.warnings)


@pytest.mark.asyncio
async def test_ai_service_successful_gemini_call(sample_request):
    service = AIService(api_key="mock_key_12345", model_name="gemini-2.5-flash")
    assert service.is_configured

    mock_json = """
    {
        "overview": "A lavish 25th anniversary celebration in Bengaluru.",
        "recommended_theme": {
            "name": "Silver Moonlight",
            "description": "Shimmering silver tones with subtle blue uplighting.",
            "color_palette": ["#C0C0C0", "#FFFFFF", "#1E3A8A"]
        },
        "budget_items": [
            {"category": "Venue", "estimated_amount": 150000, "notes": "Banquet hall"},
            {"category": "Catering", "estimated_amount": 150000, "notes": "Buffet dinner"},
            {"category": "Decoration", "estimated_amount": 75000, "notes": "Silver drapery"},
            {"category": "Entertainment", "estimated_amount": 40000, "notes": "Live band"},
            {"category": "Photography", "estimated_amount": 35000, "notes": "Portraits"},
            {"category": "Miscellaneous", "estimated_amount": 15000, "notes": "Gifts"},
            {"category": "Contingency Reserve", "estimated_amount": 35000, "notes": "Emergency buffer"}
        ],
        "checklist": ["Confirm banquet booking", "Taste caterer menu"],
        "timeline": [
            {"task": "Book Banquet", "description": "Deposit paid", "priority": "High", "category": "Venue", "days_before": 40},
            {"task": "Final headcount", "description": "Confirm seats", "priority": "Medium", "category": "RSVP", "days_before": 7}
        ],
        "decoration_suggestions": ["Silver candle stands", "Fairy light curtain"],
        "catering_suggestions": ["Welcome champagne mocktail", "Continental & Indian fusion buffet"],
        "entertainment_suggestions": ["Retro acoustic guitarist", "Couple trivia game"],
        "vendor_requirements": ["A/V technician for speeches", "Cake designer"],
        "risks": [
            {"risk": "Traffic delays during peak commute", "likelihood": "Medium", "mitigation": "Encourage metro travel or shuttle"}
        ],
        "warnings": []
    }
    """

    mock_response = MagicMock()
    mock_response.text = mock_json

    with patch.object(service._client.models, "generate_content", return_value=mock_response):
        plan = await service.generate_plan(sample_request)

    assert plan.source == "gemini"
    assert plan.model == "gemini-2.5-flash"
    assert plan.overview == "A lavish 25th anniversary celebration in Bengaluru."
    assert plan.budget.total_allocated == 500000
    assert sum(item.amount for item in plan.budget.items) == 500000
    assert "mock_key_12345" not in str(plan.model_dump())


@pytest.mark.asyncio
async def test_ai_service_handles_timeout(sample_request):
    service = AIService(api_key="mock_key", model_name="gemini-2.5-flash", timeout_seconds=0.01)

    def slow_call(*args, **kwargs):
        import time
        time.sleep(0.05)
        return MagicMock(text="{}")

    with patch.object(service._client.models, "generate_content", side_effect=slow_call):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_plan(sample_request)
        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_ai_service_handles_rate_limit(sample_request):
    service = AIService(api_key="mock_key", model_name="gemini-2.5-flash")

    rate_limit_error = errors.APIError(429, "Resource has been exhausted (e.g. check quota)")

    with patch.object(service._client.models, "generate_content", side_effect=rate_limit_error):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_plan(sample_request)
        assert exc_info.value.status_code == 429
        assert "quota" in exc_info.value.detail.lower() or "rate limit" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_ai_service_handles_auth_error(sample_request):
    service = AIService(api_key="invalid_key", model_name="gemini-2.5-flash")

    auth_error = errors.APIError(401, "API_KEY_INVALID: User not authorized")

    with patch.object(service._client.models, "generate_content", side_effect=auth_error):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_plan(sample_request)
        assert exc_info.value.status_code == 502
        assert "authentication" in exc_info.value.detail.lower() or "verify" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_ai_service_handles_empty_response(sample_request):
    service = AIService(api_key="mock_key", model_name="gemini-2.5-flash")

    mock_response = MagicMock()
    mock_response.text = ""

    with patch.object(service._client.models, "generate_content", return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_plan(sample_request)
        assert exc_info.value.status_code == 502
        assert "unusable" in exc_info.value.detail.lower() or "empty" in exc_info.value.detail.lower()
