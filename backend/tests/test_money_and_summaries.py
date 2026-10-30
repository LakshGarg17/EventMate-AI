from decimal import Decimal
import pytest
from app.services.currency import (
    from_minor,
    get_currency_exponent,
    to_minor,
    validate_and_parse_money,
)
from app.services.summary import compute_budget_summary


def test_money_exactness_helpers():
    # Decimal exactness test: 0.10 + 0.20 == 0.30
    m1 = to_minor(Decimal("0.10"), "USD")
    m2 = to_minor(Decimal("0.20"), "USD")
    assert m1 == 10
    assert m2 == 20
    assert m1 + m2 == 30
    assert from_minor(m1 + m2, "USD") == "0.30"

    # Awkward integer values
    assert to_minor(100001, "USD") == 10000100
    assert from_minor(100001, "USD") == "1000.01"

    # Zero-decimal currency: JPY
    assert get_currency_exponent("JPY") == 0
    assert to_minor("5000", "JPY") == 5000
    assert from_minor(5000, "JPY") == "5000"

    # Rejection of decimals in JPY
    with pytest.raises(ValueError):
        validate_and_parse_money("5000.5", "JPY")

    # Rejection of more than allowed decimals in USD (3 decimals)
    with pytest.raises(ValueError):
        validate_and_parse_money("100.555", "USD")

    # Rejection of negative numbers
    with pytest.raises(ValueError):
        validate_and_parse_money("-10.00", "USD")

    # Rejection of excessive value
    with pytest.raises(ValueError):
        validate_and_parse_money("1000000000000000", "USD")


def test_api_money_validation_rejections(client):
    # Negative budget rejected with 422
    res_neg = client.post("/api/events", json={
        "name": "Negative Budget",
        "event_type": "Birthday",
        "event_date": "2026-11-20",
        "location": "Venue",
        "guest_count": 10,
        "total_budget": "-500.00",
        "currency": "USD"
    })
    assert res_neg.status_code == 422

    # Excess decimals for USD (3 decimal places) rejected with 422
    res_dec = client.post("/api/events", json={
        "name": "Excess Decimals",
        "event_type": "Birthday",
        "event_date": "2026-11-20",
        "location": "Venue",
        "guest_count": 10,
        "total_budget": "100.555",
        "currency": "USD"
    })
    assert res_dec.status_code == 422

    # Decimals in zero-decimal currency JPY rejected with 422
    res_jpy = client.post("/api/events", json={
        "name": "JPY Decimals",
        "event_type": "Birthday",
        "event_date": "2026-11-20",
        "location": "Tokyo",
        "guest_count": 10,
        "total_budget": "5000.50",
        "currency": "JPY"
    })
    assert res_jpy.status_code == 422


def test_budget_summary_deterministic_calculations(client):
    # Create Event with total_budget 1000.00 USD
    event = client.post("/api/events", json={
        "name": "Budget Summary Test",
        "event_type": "Wedding",
        "event_date": "2026-11-25",
        "location": "Manhattan",
        "guest_count": 20,
        "total_budget": "1000.00",
        "currency": "USD",
        "generated_plan": {
            "budget": {
                "items": [
                    {"category": "Venue", "amount": 60000},  # 600.00
                    {"category": "Catering", "amount": 30000},  # 300.00
                ]
            }
        }
    }).json()
    event_id = event["id"]
    venue_cat_id = [c["id"] for c in event["budget_categories"] if c["category_name"] == "Venue"][0]

    # Add Expense 1 in Venue: est 500.00, act 550.00, status Paid
    client.post(f"/api/events/{event_id}/expenses", json={
        "description": "Venue Deposit",
        "estimated_amount": "500.00",
        "actual_amount": "550.00",
        "budget_category_id": venue_cat_id,
        "payment_status": "Paid"
    })

    # Add Expense 2 in Venue: est 200.00, act 50.00, status Partial (150 outstanding)
    client.post(f"/api/events/{event_id}/expenses", json={
        "description": "Venue Sound",
        "estimated_amount": "200.00",
        "actual_amount": "50.00",
        "budget_category_id": venue_cat_id,
        "payment_status": "Partial"
    })

    # Add Expense 3 Uncategorized: est 300.00, act 450.00, status Pending (300 outstanding)
    client.post(f"/api/events/{event_id}/expenses", json={
        "description": "Surprise Gift",
        "estimated_amount": "300.00",
        "actual_amount": None,
        "budget_category_id": None,
        "payment_status": "Pending"
    })

    # Total Actual = 550 + 50 + 0 = 600.00
    # Total Budget = 1000.00
    # Remaining = 400.00
    # Utilization = (600 / 1000) * 100 = 60.0%
    # Over budget = False
    # Outstanding pending = 150 + 300 = 450.00
    ev = client.get(f"/api/events/{event_id}").json()
    b_sum = ev["budget_summary"]

    assert b_sum["total_budget"] == "1000.00"
    assert b_sum["total_estimated"] == "1000.00"
    assert b_sum["total_actual"] == "600.00"
    assert b_sum["remaining"] == "400.00"
    assert b_sum["utilization_percent"] == 60.0
    assert b_sum["over_budget"] is False
    assert b_sum["pending_total"] == "450.00"
    assert len(b_sum["pending_payments"]) == 2

    # Uncategorized category exists in breakdown
    breakdown_names = [cb["category_name"] for cb in b_sum["category_breakdown"]]
    assert "Uncategorized" in breakdown_names


def test_budget_summary_over_budget_and_zero_budget_safe():
    # Zero budget safety
    res_zero = compute_budget_summary(0, "USD", [], [])
    assert res_zero["utilization_percent"] == 0.0
    assert res_zero["over_budget"] is False
    assert res_zero["remaining"] == "0.00"

    # Over budget scenario: total budget 100 minor, actual 150 minor
    class MockExpense:
        estimated_amount = 150
        actual_amount = 150
        payment_status = "Paid"
        budget_category_id = None
        id = "e1"
        description = "Big expense"

    res_over = compute_budget_summary(100, "USD", [], [MockExpense()])
    assert res_over["over_budget"] is True
    assert res_over["remaining"] == "-0.50"
    assert res_over["utilization_percent"] == 150.0
