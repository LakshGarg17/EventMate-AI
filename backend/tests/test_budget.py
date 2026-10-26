import pytest
from app.schemas import RawAIBudgetItem
from app.services.budget import reconcile_budget, REQUIRED_CATEGORIES


@pytest.mark.parametrize("total_budget", [1, 7, 100, 100001, 750000, 9999999])
def test_budget_sum_exactly_equals_total(total_budget):
    raw_items = [
        RawAIBudgetItem(category="Venue", estimated_amount=30000, notes="Hall booking"),
        RawAIBudgetItem(category="Catering", estimated_amount=30000, notes="Dinner menu"),
        RawAIBudgetItem(category="Decoration", estimated_amount=15000, notes="Floral styling"),
        RawAIBudgetItem(category="Entertainment", estimated_amount=10000, notes="DJ and audio"),
        RawAIBudgetItem(category="Photography", estimated_amount=10000, notes="Photos and film"),
        RawAIBudgetItem(category="Miscellaneous", estimated_amount=5000, notes="Printouts and favors"),
    ]
    breakdown = reconcile_budget(
        total_budget=total_budget,
        raw_items=raw_items,
        event_type="Wedding",
        currency="INR"
    )

    item_sum = sum(item.amount for item in breakdown.items)
    assert item_sum == total_budget
    assert breakdown.total_allocated == total_budget
    assert breakdown.is_estimate is True
    assert all(item.amount >= 0 for item in breakdown.items)


def test_contingency_reserve_is_always_present_and_minimum_applied():
    raw_items = [
        RawAIBudgetItem(category="Venue", estimated_amount=50000, notes="Hall"),
        RawAIBudgetItem(category="Catering", estimated_amount=50000, notes="Buffet"),
    ]
    breakdown = reconcile_budget(
        total_budget=100000,
        raw_items=raw_items,
        event_type="Birthday",
        currency="USD"
    )

    contingency_items = [item for item in breakdown.items if item.category == "Contingency Reserve"]
    assert len(contingency_items) == 1
    assert breakdown.contingency == contingency_items[0].amount
    assert breakdown.contingency > 0
    # Must be around 5-10%
    assert 5 <= contingency_items[0].percentage <= 12


def test_malformed_ai_budget_with_negatives_and_empty_list():
    # Negative amounts and missing essential categories
    raw_items = [
        RawAIBudgetItem(category="Venue", estimated_amount=-5000, notes="Invalid negative"),
        RawAIBudgetItem(category="", estimated_amount=10000, notes="Missing category"),
    ]
    breakdown = reconcile_budget(
        total_budget=50000,
        raw_items=raw_items,
        event_type="Community Event",
        currency="EUR"
    )

    assert sum(item.amount for item in breakdown.items) == 50000
    assert all(item.amount >= 0 for item in breakdown.items)
    # Check that required categories were filled in
    categories_present = {item.category for item in breakdown.items}
    for req in REQUIRED_CATEGORIES:
        assert req in categories_present


def test_all_zero_weights_fall_back_to_defaults():
    raw_items = [
        RawAIBudgetItem(category="Venue", estimated_amount=0, notes="Zero"),
        RawAIBudgetItem(category="Catering", estimated_amount=0, notes="Zero"),
    ]
    breakdown = reconcile_budget(
        total_budget=100001,
        raw_items=raw_items,
        event_type="Wedding",
        currency="INR"
    )

    assert sum(item.amount for item in breakdown.items) == 100001
    assert breakdown.total_allocated == 100001
    assert all(item.amount >= 0 for item in breakdown.items)
