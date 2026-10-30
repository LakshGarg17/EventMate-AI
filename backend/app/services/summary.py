from datetime import date, timedelta
from typing import Any, Dict, List, Optional

try:
    from app.services.currency import from_minor
    from app.services.today import get_today
except ImportError:
    from backend.app.services.currency import from_minor
    from backend.app.services.today import get_today


def compute_task_summary(tasks: List[Any], today: Optional[date] = None) -> Dict[str, Any]:
    """
    Computes deterministic task progress metrics:
    total, pending, in_progress, completed, overdue, upcoming, progress_percent.
    """
    if today is None:
        today = get_today()

    total = len(tasks)
    pending = 0
    in_progress = 0
    completed = 0
    overdue = 0
    upcoming = 0

    upcoming_cutoff = today + timedelta(days=7)

    for t in tasks:
        status = getattr(t, "status", None) or t.get("status")
        due_date = getattr(t, "due_date", None) or t.get("due_date")

        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)

        if status == "Completed":
            completed += 1
        elif status == "In Progress":
            in_progress += 1
        else:
            pending += 1

        if status != "Completed" and due_date:
            if due_date < today:
                overdue += 1
            elif today <= due_date <= upcoming_cutoff:
                upcoming += 1

    progress_percent = round((completed / total * 100.0), 1) if total > 0 else 0.0

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "upcoming": upcoming,
        "progress_percent": progress_percent,
    }


def compute_next_deadline(tasks: List[Any], today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """
    Finds the earliest not-completed task due today or later.
    Returns {title, due_date} or None.
    """
    if today is None:
        today = get_today()

    candidates = []
    for t in tasks:
        status = getattr(t, "status", None) or t.get("status")
        if status == "Completed":
            continue
        due_date = getattr(t, "due_date", None) or t.get("due_date")
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)

        if due_date and due_date >= today:
            title = getattr(t, "title", None) or t.get("title", "")
            candidates.append((due_date, title))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    earliest_date, earliest_title = candidates[0]
    return {
        "title": earliest_title,
        "due_date": earliest_date.isoformat() if hasattr(earliest_date, "isoformat") else str(earliest_date),
    }


def compute_budget_summary(
    total_budget_minor: int,
    currency: str,
    categories: List[Any],
    expenses: List[Any]
) -> Dict[str, Any]:
    """
    Deterministic budget reconciliation and expense summary computation.
    All minor unit sums are computed with integer math.
    Output strings use currency-correct decimal precision.
    """
    total_estimated_minor = 0
    total_actual_minor = 0
    pending_payments: List[Dict[str, Any]] = []
    pending_total_minor = 0

    # Categorize expenses
    cat_expenses: Dict[Optional[str], List[Any]] = {}

    for exp in expenses:
        est_minor = getattr(exp, "estimated_amount", 0) or 0
        act_minor = getattr(exp, "actual_amount", None)
        act_val = act_minor if act_minor is not None else 0

        total_estimated_minor += est_minor
        total_actual_minor += act_val

        status = getattr(exp, "payment_status", "Pending") or "Pending"
        if status in ("Pending", "Partial"):
            outstanding_minor = max(est_minor - act_val, 0)
            pending_total_minor += outstanding_minor
            exp_id = getattr(exp, "id", "")
            desc = getattr(exp, "description", "")
            pending_payments.append({
                "expense_id": exp_id,
                "description": desc,
                "payment_status": status,
                "estimated_amount": from_minor(est_minor, currency),
                "actual_amount": from_minor(act_val, currency),
                "outstanding": from_minor(outstanding_minor, currency),
            })

        cat_id = getattr(exp, "budget_category_id", None)
        if cat_id not in cat_expenses:
            cat_expenses[cat_id] = []
        cat_expenses[cat_id].append(exp)

    remaining_minor = total_budget_minor - total_actual_minor
    over_budget = total_actual_minor > total_budget_minor

    if total_budget_minor > 0:
        utilization_percent = round((total_actual_minor / total_budget_minor) * 100.0, 1)
    else:
        utilization_percent = 0.0

    category_sum_minor = sum(getattr(c, "estimated_amount", 0) for c in categories)
    unallocated_minor = total_budget_minor - category_sum_minor

    # Build category breakdown
    category_breakdown: List[Dict[str, Any]] = []
    known_cat_ids = set()

    for c in categories:
        c_id = getattr(c, "id", "")
        known_cat_ids.add(c_id)
        c_name = getattr(c, "category_name", "")
        alloc_minor = getattr(c, "estimated_amount", 0)

        exp_list = cat_expenses.get(c_id, [])
        exp_est_minor = sum(getattr(e, "estimated_amount", 0) or 0 for e in exp_list)
        exp_act_minor = sum((getattr(e, "actual_amount", 0) or 0) for e in exp_list)

        category_breakdown.append({
            "category_id": c_id,
            "category_name": c_name,
            "allocated_estimate": from_minor(alloc_minor, currency),
            "expense_estimated_total": from_minor(exp_est_minor, currency),
            "expense_actual_total": from_minor(exp_act_minor, currency),
        })

    # Uncategorized expenses (None or not matching existing categories)
    uncat_expenses = []
    for cat_id, exp_list in cat_expenses.items():
        if cat_id is None or cat_id not in known_cat_ids:
            uncat_expenses.extend(exp_list)

    if uncat_expenses:
        uncat_est_minor = sum(getattr(e, "estimated_amount", 0) or 0 for e in uncat_expenses)
        uncat_act_minor = sum((getattr(e, "actual_amount", 0) or 0) for e in uncat_expenses)
        category_breakdown.append({
            "category_id": None,
            "category_name": "Uncategorized",
            "allocated_estimate": from_minor(0, currency),
            "expense_estimated_total": from_minor(uncat_est_minor, currency),
            "expense_actual_total": from_minor(uncat_act_minor, currency),
        })

    return {
        "total_budget": from_minor(total_budget_minor, currency),
        "total_estimated": from_minor(total_estimated_minor, currency),
        "total_actual": from_minor(total_actual_minor, currency),
        "remaining": from_minor(remaining_minor, currency),
        "utilization_percent": utilization_percent,
        "over_budget": over_budget,
        "unallocated": from_minor(unallocated_minor, currency),
        "category_breakdown": category_breakdown,
        "pending_payments": pending_payments,
        "pending_total": from_minor(pending_total_minor, currency),
    }
