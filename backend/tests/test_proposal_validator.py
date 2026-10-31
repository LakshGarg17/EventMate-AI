from datetime import date
from decimal import Decimal
import pytest

from app.db.models import BudgetCategory, Event, Expense, Task
from app.schemas import AIProposalResponse, BudgetAdjustment, TaskToAdd, TaskToUpdate
from app.services.proposal_validator import normalize_task_title, validate_proposal


@pytest.fixture
def test_event():
    event = Event(
        id="ev-123",
        name="Aarav Birthday Bash",
        event_type="Birthday",
        event_date=date(2026, 12, 1),
        location="Mumbai",
        guest_count=50,
        total_budget=10000000,  # 100,000.00 INR
        currency="INR",
    )
    cat1 = BudgetCategory(id="cat-venue", event_id=event.id, category_name="Venue", estimated_amount=4000000)  # 40k
    cat2 = BudgetCategory(id="cat-cater", event_id=event.id, category_name="Catering", estimated_amount=3500000)  # 35k
    cat3 = BudgetCategory(id="cat-decor", event_id=event.id, category_name="Decoration", estimated_amount=2500000)  # 25k
    event.budget_categories = [cat1, cat2, cat3]  # total = 100,000.00 balanced

    t1 = Task(id="task-1", event_id=event.id, title="Book DJ", category="Music", priority="High", due_date=date(2026, 11, 15), status="Pending")
    t2 = Task(id="task-2", event_id=event.id, title="Order Birthday Cake", category="Catering", priority="Medium", due_date=date(2026, 11, 25), status="Completed")
    event.tasks = [t1, t2]
    event.expenses = []
    return event


def test_validate_proposal_valid_reallocation(test_event):
    raw = AIProposalResponse(
        summary="Shift 10000 from Venue to Catering",
        budget_adjustments=[
            BudgetAdjustment(category_name="Venue", delta_amount="-10000"),
            BudgetAdjustment(category_name="catering", delta_amount="+10000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is None
    assert preview["budget"]["balanced"] is True
    assert preview["budget"]["total_before"] == "100000.00"
    assert preview["budget"]["total_after"] == "100000.00"
    assert len(preview["budget"]["categories"]) == 2


def test_validate_proposal_case_insensitive_category_matching(test_event):
    raw = AIProposalResponse(
        summary="Adjust decor",
        budget_adjustments=[
            BudgetAdjustment(category_name="  dEcoRation  ", delta_amount="-5000"),
            BudgetAdjustment(category_name="cAtErInG", delta_amount="+5000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is None


def test_validate_proposal_unknown_category_rejected(test_event):
    raw = AIProposalResponse(
        summary="Bad category",
        budget_adjustments=[
            BudgetAdjustment(category_name="Rocket Science", delta_amount="-5000"),
            BudgetAdjustment(category_name="Catering", delta_amount="+5000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "Unknown category 'Rocket Science'" in error
    assert "Valid categories are:" in error


def test_validate_proposal_negative_resulting_amount_rejected(test_event):
    raw = AIProposalResponse(
        summary="Excessive cut",
        budget_adjustments=[
            BudgetAdjustment(category_name="Venue", delta_amount="-50000"),  # Venue only has 40k
            BudgetAdjustment(category_name="Catering", delta_amount="+50000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "cannot be negative" in error


def test_validate_proposal_unbalanced_deltas_rejected_when_balanced(test_event):
    raw = AIProposalResponse(
        summary="Unbalanced increase",
        budget_adjustments=[
            BudgetAdjustment(category_name="Catering", delta_amount="+20000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "Budget is currently balanced. Proposed adjustments must remain balanced" in error


def test_validate_proposal_new_total_budget_with_matching_deltas(test_event):
    raw = AIProposalResponse(
        summary="Increase overall budget by 20000 for Catering",
        new_total_budget="120000.00",
        budget_adjustments=[
            BudgetAdjustment(category_name="Catering", delta_amount="+20000"),
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is None
    assert preview["budget"]["balanced"] is True
    assert preview["budget"]["total_after"] == "120000.00"
    assert changes["new_total_budget_minor"] == 12000000


def test_validate_proposal_duplicate_task_skipped_with_warning(test_event):
    raw = AIProposalResponse(
        summary="Add tasks",
        tasks_to_add=[
            TaskToAdd(title="Book DJ", category="Music", priority="High", due_date="2026-11-10"),  # duplicate of existing task-1
            TaskToAdd(title="Decorate Photo Booth", category="Decoration", priority="Medium", due_date="2026-11-20"),
            TaskToAdd(title="decorate photo booth!", category="Decoration", priority="Low", due_date="2026-11-20"),  # duplicate within proposal
        ],
    )
    changes, preview, warnings, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is None
    assert len(preview["tasks_to_add"]) == 1
    assert preview["tasks_to_add"][0]["title"] == "Decorate Photo Booth"
    assert any("Skipped duplicate task: 'Book DJ'" in w for w in warnings)
    assert any("Skipped duplicate task: 'decorate photo booth!'" in w for w in warnings)


def test_validate_proposal_task_date_bounds_enforced(test_event):
    # Due date in past
    raw_past = AIProposalResponse(
        summary="Past task",
        tasks_to_add=[
            TaskToAdd(title="Past Task", category="General", priority="Medium", due_date="2026-10-25"),
        ],
    )
    _, _, _, err_past = validate_proposal(test_event, raw_past, today=date(2026, 10, 30))
    assert err_past is not None
    assert "must be between today" in err_past

    # Due date after event date (2026-12-01)
    raw_future = AIProposalResponse(
        summary="Future task",
        tasks_to_add=[
            TaskToAdd(title="Future Task", category="General", priority="Medium", due_date="2026-12-05"),
        ],
    )
    _, _, _, err_future = validate_proposal(test_event, raw_future, today=date(2026, 10, 30))
    assert err_future is not None
    assert "must be between today" in err_future


def test_validate_proposal_completed_task_cannot_be_updated(test_event):
    # task-2 is Completed
    raw = AIProposalResponse(
        summary="Update completed task",
        tasks_to_update=[
            TaskToUpdate(task_id="task-2", priority="High"),
        ],
    )
    _, _, _, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "Cannot update completed task" in error


def test_validate_proposal_foreign_task_id_rejected(test_event):
    raw = AIProposalResponse(
        summary="Update foreign task",
        tasks_to_update=[
            TaskToUpdate(task_id="foreign-task-999", priority="High"),
        ],
    )
    _, _, _, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "does not belong to this event" in error


def test_validate_proposal_empty_result_is_error(test_event):
    raw = AIProposalResponse(
        summary="No changes",
    )
    _, _, _, error = validate_proposal(test_event, raw, today=date(2026, 10, 30))
    assert error is not None
    assert "No valid changes to apply" in error

