import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from google.genai import errors

from app.db.models import BudgetCategory, Event, Expense, Task, Vendor
from app.services.ai_service import AIService
from app.services.event_context import build_event_context
from app.services.today import get_now, set_frozen_now


class SimpleResponseModel(BaseModel):
    message: str
    count: int


def test_today_get_now_and_freeze():
    now_default = get_now()
    assert now_default.tzinfo is not None

    frozen_dt = datetime(2026, 10, 30, 15, 30, tzinfo=timezone.utc)
    set_frozen_now(frozen_dt)
    assert get_now() == frozen_dt

    set_frozen_now(None)
    assert get_now() != frozen_dt


def test_build_event_context_fields_and_redaction(temp_db):
    SessionLocal = temp_db["SessionLocal"]
    with SessionLocal() as db:
        event = Event(
            name="Rohit & Priya Sangeet",
            event_type="Wedding",
            event_date=date(2026, 12, 15),
            location="Taj Palace, New Delhi",
            guest_count=200,
            total_budget=50000000,  # 500,000.00 INR
            currency="INR",
            preferred_theme="Royal Marigold",
            additional_preferences="Pure vegetarian catering with Jain options",
            generated_plan={
                "overview": "A magnificent sangeet celebration",
                "recommended_theme": {"name": "Royal Marigold"},
            },
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        cat1 = BudgetCategory(event_id=event.id, category_name="Venue", estimated_amount=20000000)
        cat2 = BudgetCategory(event_id=event.id, category_name="Catering", estimated_amount=20000000)
        db.add_all([cat1, cat2])
        db.commit()
        db.refresh(cat1)

        exp = Expense(
            event_id=event.id,
            budget_category_id=cat1.id,
            description="Venue Advance Deposit",
            estimated_amount=10000000,
            actual_amount=10000000,
            payment_status="Paid",
        )
        task = Task(
            event_id=event.id,
            title="Book Dhol Players",
            category="Entertainment",
            priority="High",
            due_date=date(2026, 11, 20),
            status="Pending",
        )
        vendor = Vendor(
            event_id=event.id,
            name="Delhi Dhol Troupe",
            category="Entertainment",
            contact_info="CONFIDENTIAL_PHONE_9999999999 email: secret@dhol.com",
            quoted_amount=4500000,  # 45,000.00
            notes="Requires green room and refreshments",
            status="Shortlisted",
        )
        db.add_all([exp, task, vendor])
        db.commit()

        context_dict, rendered_text = build_event_context(event.id, db=db, today=date(2026, 10, 30))

        assert context_dict["event"]["name"] == "Rohit & Priya Sangeet"
        assert context_dict["event"]["currency"] == "INR"
        assert context_dict["today"] == "2026-10-30"

        # Check server-computed summaries
        assert context_dict["budget_summary"]["total_budget"] == "500000.00"
        assert context_dict["task_summary"]["total"] == 1

        # Check categories
        assert any(c["name"] == "Venue" for c in context_dict["categories"])

        # Check task included with task_id
        assert len(context_dict["tasks"]) == 1
        assert context_dict["tasks"][0]["task_id"] == task.id
        assert context_dict["tasks"][0]["title"] == "Book Dhol Players"

        # Check vendor included but contact_info excluded!
        assert len(context_dict["vendors"]) == 1
        assert context_dict["vendors"][0]["name"] == "Delhi Dhol Troupe"
        assert "contact_info" not in context_dict["vendors"][0]
        assert "CONFIDENTIAL_PHONE_9999999999" not in rendered_text
        assert "secret@dhol.com" not in rendered_text

        # Check prompt injection hygiene
        assert rendered_text.startswith("<event_context>")
        assert rendered_text.endswith("</event_context>")
        assert "Delhi Dhol Troupe" in rendered_text
        assert "Book Dhol Players" in rendered_text


@pytest.mark.asyncio
async def test_generate_structured_success():
    service = AIService(api_key="fake_key", model_name="gemini-2.5-flash")
    mock_response = MagicMock()
    mock_response.text = '{"message": "Hello event planner", "count": 42}'

    with patch.object(service._client.models, "generate_content", return_value=mock_response):
        result, source, model = await service.generate_structured(
            system_prompt="You are a helper",
            user_prompt="Give me greeting",
            response_model=SimpleResponseModel,
        )
        assert result.message == "Hello event planner"
        assert result.count == 42
        assert source == "gemini"
        assert model == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_generate_structured_repair_retry():
    service = AIService(api_key="fake_key", model_name="gemini-2.5-flash")
    bad_response = MagicMock()
    bad_response.text = '{"message": "Broken JSON missing count"}'

    good_response = MagicMock()
    good_response.text = '{"message": "Fixed JSON", "count": 10}'

    with patch.object(service._client.models, "generate_content", side_effect=[bad_response, good_response]) as mock_gen:
        result, source, model = await service.generate_structured(
            system_prompt="You are a helper",
            user_prompt="Give me data",
            response_model=SimpleResponseModel,
        )
        assert result.message == "Fixed JSON"
        assert result.count == 10
        assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_generate_structured_timeout():
    service = AIService(api_key="fake_key", model_name="gemini-2.5-flash", timeout_seconds=0.01)

    def slow_call(*args, **kwargs):
        import time
        time.sleep(0.05)
        return MagicMock(text='{"message": "too late", "count": 1}')

    with patch.object(service._client.models, "generate_content", side_effect=slow_call):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_structured(
                system_prompt="sys",
                user_prompt="user",
                response_model=SimpleResponseModel,
            )
        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_generate_structured_rate_limit():
    service = AIService(api_key="fake_key", model_name="gemini-2.5-flash")
    api_err = errors.APIError(429, "Resource has been exhausted (rate limit)")

    with patch.object(service._client.models, "generate_content", side_effect=api_err):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_structured(
                system_prompt="sys",
                user_prompt="user",
                response_model=SimpleResponseModel,
            )
        assert exc_info.value.status_code == 429
