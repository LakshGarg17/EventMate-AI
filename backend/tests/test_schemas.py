from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from app.schemas import EventRequest


def test_valid_event_request():
    tomorrow = date.today() + timedelta(days=1)
    req = EventRequest(
        event_name="  Grand Annual Gala  ",
        event_type="Community Event",
        event_date=tomorrow,
        location="  Town Hall  ",
        guest_count=250,
        total_budget=500000,
        currency="INR",
        theme="  Vintage Gold  ",
        additional_preferences="  Eco-friendly decorations only  "
    )
    assert req.event_name == "Grand Annual Gala"
    assert req.location == "Town Hall"
    assert req.theme == "Vintage Gold"
    assert req.additional_preferences == "Eco-friendly decorations only"
    assert req.currency == "INR"


def test_empty_event_name_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="   ",
            event_type="Wedding",
            event_date=tomorrow,
            location="Beach Resort",
            guest_count=50,
            total_budget=100000,
        )


def test_past_event_date_raises():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValidationError) as exc:
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=yesterday,
            location="Downtown Cafe",
            guest_count=20,
            total_budget=25000,
        )
    assert "Event date must be today" in str(exc.value)


def test_zero_guest_count_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=tomorrow,
            location="Downtown Cafe",
            guest_count=0,
            total_budget=25000,
        )


def test_negative_guest_count_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=tomorrow,
            location="Downtown Cafe",
            guest_count=-5,
            total_budget=25000,
        )


def test_zero_budget_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=tomorrow,
            location="Downtown Cafe",
            guest_count=20,
            total_budget=0,
        )


def test_negative_budget_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=tomorrow,
            location="Downtown Cafe",
            guest_count=20,
            total_budget=-5000,
        )


def test_invalid_currency_raises():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        EventRequest(
            event_name="Birthday Party",
            event_type="Birthday",
            event_date=tomorrow,
            location="Downtown Cafe",
            guest_count=20,
            total_budget=10000,
            currency="XYZ",
        )
