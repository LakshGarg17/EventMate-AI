"""
Deterministic proposal validation and normalization engine.
Validates all proposed plan changes against live database entities and business rules.
Guarantees:
- Pure deterministic function without side effects.
- Strict category matching (case-insensitive).
- All arithmetic in integer minor units.
- Balanced budget preservation and gap reduction rules.
- Task date bounds (today <= due_date <= event_date).
- Deduplication of tasks with visible warnings.
- Disallows completed task updates.
- Rejects any unauthorized operations.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from app.db.models import BudgetCategory, Event, Task
    from app.schemas import AIProposalResponse
    from app.services.currency import (
        MAX_MAJOR_UNITS,
        from_minor,
        get_currency_exponent,
        validate_and_parse_money,
    )
except ImportError:
    from backend.app.db.models import BudgetCategory, Event, Task
    from backend.app.schemas import AIProposalResponse
    from backend.app.services.currency import (
        MAX_MAJOR_UNITS,
        from_minor,
        get_currency_exponent,
        validate_and_parse_money,
    )


def normalize_task_title(title: str) -> str:
    """Normalizes title for duplicate detection: casefold, strip punctuation and whitespace."""
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]", "", title.casefold())


def parse_signed_money_delta(value_str: str, currency: str, field_name: str) -> int:
    """
    Parses a signed decimal string into integer minor units.
    Rejects NaN, infinity, excessive decimals, and absurd magnitudes.
    """
    if not value_str or not isinstance(value_str, str):
        raise ValueError(f"{field_name} must be a valid numeric string")

    clean_str = value_str.strip().lstrip("+")
    try:
        dec = Decimal(clean_str)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} '{value_str}' is not a valid numeric amount")

    if dec.is_nan() or dec.is_infinite():
        raise ValueError(f"{field_name} must be a finite number")

    if abs(dec) > MAX_MAJOR_UNITS:
        raise ValueError(f"{field_name} exceeds maximum permitted limit")

    exp = get_currency_exponent(currency)
    if dec.as_tuple().exponent < -exp:
        raise ValueError(
            f"{field_name} has more decimal places than allowed for currency '{currency}' ({exp} allowed)"
        )

    factor = Decimal(10 ** exp)
    return int((dec * factor).to_integral_exact())


def validate_proposal(
    event: Event,
    raw_proposal: AIProposalResponse,
    today: date,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[str], Optional[str]]:
    """
    Validates and normalizes raw AI proposal against event state.
    Returns (normalized_changes, preview_dict, warnings, error_message).
    If error_message is not None, validation failed.
    """
    currency = event.currency
    warnings: List[str] = []
    categories: List[BudgetCategory] = event.budget_categories or []
    tasks: List[Task] = event.tasks or []
    expenses = event.expenses or []

    # Map category name case-insensitive to BudgetCategory
    cat_by_name = {c.category_name.strip().casefold(): c for c in categories}
    valid_cat_names = ", ".join(f"'{c.category_name}'" for c in sorted(categories, key=lambda c: c.category_name))

    # --- 1. Total Budget Validation ---
    new_total_minor = event.total_budget
    total_budget_changed = False
    if raw_proposal.new_total_budget:
        try:
            parsed_dec = validate_and_parse_money(
                raw_proposal.new_total_budget,
                currency=currency,
                field_name="new_total_budget",
            )
            if parsed_dec <= 0:
                return None, None, [], "new_total_budget must be greater than zero."
            exp = get_currency_exponent(currency)
            new_total_minor = int((parsed_dec * (10 ** exp)).to_integral_exact())
            total_budget_changed = (new_total_minor != event.total_budget)
        except ValueError as e:
            return None, None, [], f"Invalid new_total_budget: {str(e)}"

    # --- 2. Budget Adjustments Validation ---
    adjustments = raw_proposal.budget_adjustments or []
    if len(adjustments) > 12:
        return None, None, [], "At most 12 budget adjustments are allowed per proposal."

    if adjustments and not categories:
        return None, None, [], "Event has no budget categories; cannot apply budget adjustments."

    deltas_by_cat_id: Dict[str, int] = {}
    seen_adj_names: Set[str] = set()

    for adj in adjustments:
        clean_name = adj.category_name.strip()
        folded_name = clean_name.casefold()

        if folded_name not in cat_by_name:
            return (
                None,
                None,
                [],
                f"Unknown category '{adj.category_name}'. Valid categories are: {valid_cat_names}.",
            )

        if folded_name in seen_adj_names:
            return None, None, [], f"Duplicate adjustment for category '{adj.category_name}' is not allowed."
        seen_adj_names.add(folded_name)

        matched_cat = cat_by_name[folded_name]
        try:
            delta_minor = parse_signed_money_delta(
                adj.delta_amount,
                currency=currency,
                field_name=f"delta for {matched_cat.category_name}",
            )
        except ValueError as e:
            return None, None, [], str(e)

        if delta_minor != 0:
            deltas_by_cat_id[matched_cat.id] = delta_minor

    # Check resulting category amounts
    new_cat_amounts: Dict[str, int] = {}
    for c in categories:
        delta = deltas_by_cat_id.get(c.id, 0)
        res_amt = c.estimated_amount + delta
        if res_amt < 0:
            return (
                None,
                None,
                [],
                f"Budget for category '{c.category_name}' cannot be negative ({from_minor(res_amt, currency)}).",
            )
        new_cat_amounts[c.id] = res_amt

    # --- 3. Consistency Rule (Balanced Budget check) ---
    current_cat_sum = sum(c.estimated_amount for c in categories)
    new_cat_sum = sum(new_cat_amounts.values()) if categories else new_total_minor
    before_gap = abs(current_cat_sum - event.total_budget)
    after_gap = abs(new_cat_sum - new_total_minor)

    if before_gap == 0:
        if after_gap != 0:
            return (
                None,
                None,
                [],
                f"Budget is currently balanced. Proposed adjustments must remain balanced "
                f"(allocated: {from_minor(new_cat_sum, currency)}, total: {from_minor(new_total_minor, currency)}).",
            )
    else:
        if after_gap > before_gap:
            return (
                None,
                None,
                [],
                f"Proposed changes increase budget imbalance from {from_minor(before_gap, currency)} "
                f"to {from_minor(after_gap, currency)} {currency}.",
            )
        elif after_gap > 0:
            warnings.append(
                f"Budget remains unbalanced with an allocation gap of {from_minor(after_gap, currency)} {currency}."
            )

    # Warnings for category drops below expenses and total spend
    for c in categories:
        if c.id in deltas_by_cat_id and deltas_by_cat_id[c.id] < 0:
            cat_exp_est = sum(e.estimated_amount for e in expenses if e.budget_category_id == c.id)
            if new_cat_amounts[c.id] < cat_exp_est:
                warnings.append(
                    f"Category '{c.category_name}' allocation ({from_minor(new_cat_amounts[c.id], currency)}) "
                    f"drops below assigned expense estimates ({from_minor(cat_exp_est, currency)})."
                )

    total_actual_spend = sum(e.actual_amount or 0 for e in expenses)
    if new_total_minor < total_actual_spend:
        warnings.append(
            f"New total budget ({from_minor(new_total_minor, currency)}) is below actual spend to date "
            f"({from_minor(total_actual_spend, currency)})."
        )

    if event.event_date < today:
        warnings.append("The event date has already passed.")

    # --- 4. Tasks to Add Validation ---
    proposed_tasks_add = raw_proposal.tasks_to_add or []
    if len(proposed_tasks_add) > 10:
        return None, None, [], "At most 10 tasks can be added in a single proposal."

    existing_task_titles_norm = {normalize_task_title(t.title) for t in tasks}
    seen_add_titles_norm: Set[str] = set()
    normalized_tasks_to_add: List[Dict[str, Any]] = []

    for t_add in proposed_tasks_add:
        title = t_add.title.strip()
        if not (1 <= len(title) <= 120):
            return None, None, [], f"Task title '{title[:30]}...' must be between 1 and 120 characters."

        category_name = t_add.category.strip()
        if not (1 <= len(category_name) <= 50):
            return None, None, [], f"Task category '{category_name[:30]}' must be between 1 and 50 characters."

        if t_add.priority not in ("High", "Medium", "Low"):
            return None, None, [], f"Task priority '{t_add.priority}' must be High, Medium, or Low."

        try:
            due_d = date.fromisoformat(t_add.due_date.strip())
        except (ValueError, AttributeError):
            return None, None, [], f"Invalid task due_date '{t_add.due_date}'. Must be ISO date (YYYY-MM-DD)."

        if due_d < today or due_d > event.event_date:
            return (
                None,
                None,
                [],
                f"Task due date ({due_d.isoformat()}) must be between today ({today.isoformat()}) "
                f"and event date ({event.event_date.isoformat()}).",
            )

        norm_title = normalize_task_title(title)
        if norm_title in existing_task_titles_norm or norm_title in seen_add_titles_norm:
            warnings.append(f"Skipped duplicate task: '{title}'")
            continue

        seen_add_titles_norm.add(norm_title)
        normalized_tasks_to_add.append({
            "title": title,
            "description": t_add.description.strip() if t_add.description else None,
            "category": category_name,
            "priority": t_add.priority,
            "due_date": due_d.isoformat(),
        })

    # --- 5. Tasks to Update Validation ---
    proposed_tasks_update = raw_proposal.tasks_to_update or []
    if len(proposed_tasks_update) > 10:
        return None, None, [], "At most 10 tasks can be updated in a single proposal."

    tasks_by_id = {t.id: t for t in tasks}
    normalized_tasks_to_update: List[Dict[str, Any]] = []
    seen_update_ids: Set[str] = set()

    for t_up in proposed_tasks_update:
        tid = t_up.task_id.strip()
        if tid not in tasks_by_id:
            return None, None, [], f"Task id '{tid}' does not belong to this event."

        if tid in seen_update_ids:
            return None, None, [], f"Duplicate update for task id '{tid}'."
        seen_update_ids.add(tid)

        existing_task = tasks_by_id[tid]
        if existing_task.status == "Completed":
            return None, None, [], f"Cannot update completed task '{existing_task.title}'."

        new_priority = t_up.priority or existing_task.priority
        if new_priority not in ("High", "Medium", "Low"):
            return None, None, [], f"Invalid priority '{new_priority}'."

        new_due_d = existing_task.due_date
        if t_up.due_date:
            try:
                parsed_due = date.fromisoformat(t_up.due_date.strip())
            except (ValueError, AttributeError):
                return None, None, [], f"Invalid task due_date '{t_up.due_date}'."

            if parsed_due < today or parsed_due > event.event_date:
                return (
                    None,
                    None,
                    [],
                    f"Updated due date ({parsed_due.isoformat()}) must be between today ({today.isoformat()}) "
                    f"and event date ({event.event_date.isoformat()}).",
                )
            new_due_d = parsed_due

        # Only record if something actually changed
        if new_priority != existing_task.priority or new_due_d != existing_task.due_date:
            normalized_tasks_to_update.append({
                "task_id": tid,
                "title": existing_task.title,
                "old_priority": existing_task.priority,
                "new_priority": new_priority,
                "old_due_date": existing_task.due_date.isoformat(),
                "new_due_date": new_due_d.isoformat(),
            })

    # --- 6. Emptiness Check ---
    has_budget_changes = bool(deltas_by_cat_id or total_budget_changed)
    has_task_changes = bool(normalized_tasks_to_add or normalized_tasks_to_update)

    if not has_budget_changes and not has_task_changes:
        return None, None, [], "No valid changes to apply."

    # --- 7. Build Preview and Normalized Changes ---
    affected_categories_preview = []
    for c in sorted(categories, key=lambda c: c.category_name):
        if c.id in deltas_by_cat_id:
            delta = deltas_by_cat_id[c.id]
            res_amt = new_cat_amounts[c.id]
            affected_categories_preview.append({
                "name": c.category_name,
                "before": from_minor(c.estimated_amount, currency),
                "after": from_minor(res_amt, currency),
                "delta": f"+{from_minor(delta, currency)}" if delta > 0 else from_minor(delta, currency),
            })

    preview: Dict[str, Any] = {
        "budget": {
            "categories": affected_categories_preview,
            "total_before": from_minor(event.total_budget, currency),
            "total_after": from_minor(new_total_minor, currency),
            "allocated_before": from_minor(current_cat_sum, currency),
            "allocated_after": from_minor(new_cat_sum, currency),
            "balanced": (new_cat_sum == new_total_minor),
        },
        "tasks_to_add": normalized_tasks_to_add,
        "tasks_to_update": normalized_tasks_to_update,
        "unchanged": "Expenses and the original AI plan are not modified.",
    }

    normalized_changes: Dict[str, Any] = {
        "new_total_budget_minor": new_total_minor if total_budget_changed else None,
        "category_deltas": [
            {
                "category_id": c_id,
                "delta_minor": delta,
                "new_amount_minor": new_cat_amounts[c_id],
            }
            for c_id, delta in deltas_by_cat_id.items()
        ],
        "tasks_to_add": normalized_tasks_to_add,
        "tasks_to_update": [
            {
                "task_id": u["task_id"],
                "priority": u["new_priority"],
                "due_date": u["new_due_date"],
            }
            for u in normalized_tasks_to_update
        ],
    }

    return normalized_changes, preview, warnings, None

