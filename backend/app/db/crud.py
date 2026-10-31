from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

try:
    from app.db.models import BudgetCategory, Event, Expense, Task, Vendor
    from app.schemas import (
        BudgetCategoryResponse,
        BudgetSummaryResponse,
        CategoryBreakdownItem,
        EventDetailResponse,
        EventSummaryResponse,
        ExpenseResponse,
        NextDeadlineInfo,
        PendingPaymentItem,
        TaskCounts,
        TaskResponse,
        TaskSummaryResponse,
        VendorResponse,
    )
    from app.services.currency import from_minor
    from app.services.summary import (
        compute_budget_summary,
        compute_next_deadline,
        compute_task_summary,
    )
    from app.services.today import get_today
except ImportError:
    from backend.app.db.models import BudgetCategory, Event, Expense, Task, Vendor
    from backend.app.schemas import (
        BudgetCategoryResponse,
        BudgetSummaryResponse,
        CategoryBreakdownItem,
        EventDetailResponse,
        EventSummaryResponse,
        ExpenseResponse,
        NextDeadlineInfo,
        PendingPaymentItem,
        TaskCounts,
        TaskResponse,
        TaskSummaryResponse,
        VendorResponse,
    )
    from backend.app.services.currency import from_minor
    from backend.app.services.summary import (
        compute_budget_summary,
        compute_next_deadline,
        compute_task_summary,
    )
    from backend.app.services.today import get_today


def format_task_response(task: Task, event_date: date, today: Optional[date] = None) -> TaskResponse:
    if today is None:
        today = get_today()
    is_overdue = task.due_date < today and task.status != "Completed"
    is_upcoming = task.status != "Completed" and today <= task.due_date <= (today + timedelta(days=7))
    after_event_date = task.due_date > event_date

    return TaskResponse(
        id=task.id,
        event_id=task.event_id,
        title=task.title,
        description=task.description,
        category=task.category,
        priority=task.priority,
        due_date=task.due_date,
        status=task.status,
        is_overdue=is_overdue,
        is_upcoming=is_upcoming,
        after_event_date=after_event_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def format_expense_response(expense: Expense, currency: str) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        event_id=expense.event_id,
        budget_category_id=expense.budget_category_id,
        description=expense.description,
        estimated_amount=from_minor(expense.estimated_amount, currency),
        actual_amount=from_minor(expense.actual_amount, currency) if expense.actual_amount is not None else None,
        payment_status=expense.payment_status,
        expense_date=expense.expense_date,
        notes=expense.notes,
        created_at=expense.created_at,
    )


def format_category_response(category: BudgetCategory, currency: str) -> BudgetCategoryResponse:
    return BudgetCategoryResponse(
        id=category.id,
        event_id=category.event_id,
        category_name=category.category_name,
        estimated_amount=from_minor(category.estimated_amount, currency),
        description=category.description,
    )


def format_vendor_response(vendor: Vendor, currency: str) -> VendorResponse:
    return VendorResponse(
        id=vendor.id,
        event_id=vendor.event_id,
        name=vendor.name,
        category=vendor.category,
        contact_info=vendor.contact_info,
        quoted_amount=from_minor(vendor.quoted_amount, currency) if vendor.quoted_amount is not None else None,
        notes=vendor.notes,
        status=vendor.status,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


def build_event_detail_response(
    event: Event,
    warnings: Optional[List[str]] = None,
    today: Optional[date] = None
) -> EventDetailResponse:
    if today is None:
        today = get_today()

    categories = event.budget_categories or []
    expenses = event.expenses or []
    tasks = event.tasks or []

    # Sort categories alphabetically
    categories_sorted = sorted(categories, key=lambda c: c.category_name)
    # Sort expenses by created_at ascending
    expenses_sorted = sorted(expenses, key=lambda e: e.created_at)
    # Sort tasks chronologically: due_date asc, created_at asc
    tasks_sorted = sorted(tasks, key=lambda t: (t.due_date, t.created_at))

    b_sum_data = compute_budget_summary(event.total_budget, event.currency, categories, expenses)
    t_sum_data = compute_task_summary(tasks, today=today)

    budget_summary = BudgetSummaryResponse(
        total_budget=b_sum_data["total_budget"],
        total_estimated=b_sum_data["total_estimated"],
        total_actual=b_sum_data["total_actual"],
        remaining=b_sum_data["remaining"],
        utilization_percent=b_sum_data["utilization_percent"],
        over_budget=b_sum_data["over_budget"],
        unallocated=b_sum_data["unallocated"],
        category_breakdown=[CategoryBreakdownItem(**item) for item in b_sum_data["category_breakdown"]],
        pending_payments=[PendingPaymentItem(**item) for item in b_sum_data["pending_payments"]],
        pending_total=b_sum_data["pending_total"],
    )

    task_summary = TaskSummaryResponse(**t_sum_data)

    cat_responses = [format_category_response(c, event.currency) for c in categories_sorted]
    exp_responses = [format_expense_response(e, event.currency) for e in expenses_sorted]
    tsk_responses = [format_task_response(t, event.event_date, today=today) for t in tasks_sorted]

    return EventDetailResponse(
        id=event.id,
        name=event.name,
        event_type=event.event_type,
        event_date=event.event_date,
        location=event.location,
        guest_count=event.guest_count,
        total_budget=from_minor(event.total_budget, event.currency),
        currency=event.currency,
        preferred_theme=event.preferred_theme,
        additional_preferences=event.additional_preferences,
        generated_plan=event.generated_plan,
        created_at=event.created_at,
        updated_at=event.updated_at,
        budget_categories=cat_responses,
        expenses=exp_responses,
        tasks=tsk_responses,
        budget_summary=budget_summary,
        task_summary=task_summary,
        warnings=warnings or [],
    )


def build_event_summary_response(event: Event, today: Optional[date] = None) -> EventSummaryResponse:
    if today is None:
        today = get_today()

    categories = event.budget_categories or []
    expenses = event.expenses or []
    tasks = event.tasks or []

    b_sum = compute_budget_summary(event.total_budget, event.currency, categories, expenses)
    t_sum = compute_task_summary(tasks, today=today)
    next_dl_data = compute_next_deadline(tasks, today=today)

    next_deadline = None
    if next_dl_data:
        dl_date = date.fromisoformat(next_dl_data["due_date"]) if isinstance(next_dl_data["due_date"], str) else next_dl_data["due_date"]
        next_deadline = NextDeadlineInfo(title=next_dl_data["title"], due_date=dl_date)

    task_counts = TaskCounts(
        total=t_sum["total"],
        completed=t_sum["completed"],
        overdue=t_sum["overdue"]
    )

    return EventSummaryResponse(
        id=event.id,
        name=event.name,
        event_type=event.event_type,
        event_date=event.event_date,
        location=event.location,
        guest_count=event.guest_count,
        total_budget=b_sum["total_budget"],
        currency=event.currency,
        budget_utilization_percent=b_sum["utilization_percent"],
        total_actual=b_sum["total_actual"],
        task_progress_percent=t_sum["progress_percent"],
        task_counts=task_counts,
        next_deadline=next_deadline,
        total_tasks=t_sum["total"],
        completed_tasks=t_sum["completed"],
        overdue_tasks=t_sum["overdue"],
    )


def get_event_with_relations(db: Session, event_id: str) -> Optional[Event]:
    stmt = (
        select(Event)
        .options(
            selectinload(Event.budget_categories),
            selectinload(Event.expenses),
            selectinload(Event.tasks),
            selectinload(Event.vendors),
        )
        .where(Event.id == event_id)
    )
    return db.scalars(stmt).first()
