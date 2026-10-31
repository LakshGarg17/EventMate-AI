"""
Deterministic event context builder for AI assistant, proposals, and styling.
Extracts event parameters, server-computed summaries, categories, tasks, expenses, and vendors,
enforcing caps, redactions, and prompt injection defense.
"""

from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

try:
    from app.db.database import SessionLocal
    from app.db.models import Event, Vendor
    from app.services.currency import from_minor
    from app.services.prompts import format_untrusted_block
    from app.services.summary import compute_budget_summary, compute_task_summary
    from app.services.today import get_today
except ImportError:
    from backend.app.db.database import SessionLocal
    from backend.app.db.models import Event, Vendor
    from backend.app.services.currency import from_minor
    from backend.app.services.prompts import format_untrusted_block
    from backend.app.services.summary import compute_budget_summary, compute_task_summary
    from backend.app.services.today import get_today


def truncate_text(text: Optional[str], max_len: int = 300) -> str:
    if not text:
        return ""
    text_clean = text.strip()
    if len(text_clean) <= max_len:
        return text_clean
    return text_clean[:max_len] + "..."


def build_event_context(
    event_id: str,
    db: Optional[Session] = None,
    today: Optional[date] = None,
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Builds a deterministic compact context dict and a rendered text representation.
    Guarantees:
    - Session is closed promptly if created locally.
    - Vendor contact_info and internal database IDs (except task_id) are excluded.
    - Server-computed summaries are used (model never computes arithmetic).
    - Caps: max 50 tasks, 50 expenses, 30 vendors.
    - Long strings truncated to 300 chars.
    """
    if db is None:
        with SessionLocal() as session:
            return _build_context_from_session(event_id, session, today)
    else:
        return _build_context_from_session(event_id, db, today)


def _build_context_from_session(
    event_id: str,
    db: Session,
    today: Optional[date] = None,
) -> Optional[Tuple[Dict[str, Any], str]]:
    if today is None:
        today = get_today()

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
    event = db.scalars(stmt).first()
    if not event:
        return None

    currency = event.currency
    categories = event.budget_categories or []
    expenses = event.expenses or []
    tasks = event.tasks or []
    vendors = event.vendors or []

    # Map category ID to Category Name for expenses
    cat_map: Dict[str, str] = {c.id: c.category_name for c in categories}

    # Compute server-side summaries
    budget_summary = compute_budget_summary(event.total_budget, currency, categories, expenses)
    task_summary = compute_task_summary(tasks, today=today)

    # Categories list
    categories_context = [
        {
            "name": c.category_name,
            "allocated_amount": from_minor(c.estimated_amount, currency),
            "description": truncate_text(c.description, 300),
        }
        for c in sorted(categories, key=lambda c: c.category_name)
    ]

    # Expenses capped at 50, sorted by created_at
    expenses_sorted = sorted(expenses, key=lambda e: e.created_at)[:50]
    expenses_context = [
        {
            "description": truncate_text(e.description, 300),
            "category": cat_map.get(e.budget_category_id or "", "Uncategorized"),
            "estimated_amount": from_minor(e.estimated_amount, currency),
            "actual_amount": from_minor(e.actual_amount, currency) if e.actual_amount is not None else None,
            "payment_status": e.payment_status,
        }
        for e in expenses_sorted
    ]

    # Tasks capped at 50, sorted by due_date asc
    upcoming_cutoff = today + timedelta(days=7)
    tasks_sorted = sorted(tasks, key=lambda t: (t.due_date, t.created_at))[:50]
    tasks_context = [
        {
            "task_id": t.id,
            "title": truncate_text(t.title, 300),
            "category": truncate_text(t.category, 50),
            "priority": t.priority,
            "due_date": t.due_date.isoformat(),
            "status": t.status,
            "is_overdue": t.due_date < today and t.status != "Completed",
            "is_upcoming": t.status != "Completed" and today <= t.due_date <= upcoming_cutoff,
        }
        for t in tasks_sorted
    ]

    # Vendors capped at 30, sorted by name (EXCLUDING contact_info and internal IDs)
    vendors_sorted = sorted(vendors, key=lambda v: v.name)[:30]
    vendors_context = [
        {
            "name": truncate_text(v.name, 100),
            "category": v.category,
            "status": v.status,
            "quote": from_minor(v.quoted_amount, currency) if v.quoted_amount is not None else None,
            "notes": truncate_text(v.notes, 300) if v.notes else None,
        }
        for v in vendors_sorted
    ]

    # Stored plan summary
    plan_theme = "None"
    plan_overview = "No stored plan"
    if event.generated_plan and isinstance(event.generated_plan, dict):
        rec_theme = event.generated_plan.get("recommended_theme")
        if isinstance(rec_theme, dict):
            plan_theme = rec_theme.get("name", "None")
        elif isinstance(rec_theme, str):
            plan_theme = rec_theme
        plan_overview = truncate_text(event.generated_plan.get("overview") or "", 300)
    elif event.preferred_theme:
        plan_theme = event.preferred_theme

    context_dict: Dict[str, Any] = {
        "today": today.isoformat(),
        "event": {
            "name": truncate_text(event.name, 100),
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat(),
            "location": truncate_text(event.location, 200),
            "guest_count": event.guest_count,
            "total_budget": from_minor(event.total_budget, currency),
            "currency": currency,
            "preferred_theme": truncate_text(event.preferred_theme, 100),
            "additional_preferences": truncate_text(event.additional_preferences, 300),
        },
        "budget_summary": budget_summary,
        "task_summary": task_summary,
        "categories": categories_context,
        "expenses": expenses_context,
        "tasks": tasks_context,
        "vendors": vendors_context,
        "stored_plan": {
            "theme": plan_theme,
            "overview": plan_overview,
        },
    }

    # Render clean text block with prompt injection hygiene
    lines = [
        f"Today's Date: {today.isoformat()}",
        f"Event Name: {event.name}",
        f"Event Type: {event.event_type}",
        f"Event Date: {event.event_date.isoformat()}",
        f"Location: {event.location}",
        f"Guest Count: {event.guest_count}",
        f"Total Budget: {currency} {from_minor(event.total_budget, currency)}",
        f"Preferred Theme: {event.preferred_theme or 'None'}",
        f"Additional Preferences: {event.additional_preferences or 'None'}",
        "",
        "--- SERVER-COMPUTED BUDGET SUMMARY ---",
        f"Total Budget: {currency} {budget_summary['total_budget']}",
        f"Total Estimated Expenses: {currency} {budget_summary['total_estimated']}",
        f"Total Actual Spent: {currency} {budget_summary['total_actual']}",
        f"Remaining Spendable: {currency} {budget_summary['remaining']}",
        f"Utilization: {budget_summary['utilization_percent']}%",
        f"Over Budget: {budget_summary['over_budget']}",
        f"Pending Payments Total: {currency} {budget_summary['pending_total']}",
        "",
        "--- BUDGET CATEGORIES ---",
    ]

    for cat in categories_context:
        lines.append(f"- {cat['name']}: {currency} {cat['allocated_amount']}")

    lines.extend([
        "",
        "--- SERVER-COMPUTED TASK SUMMARY ---",
        f"Total Tasks: {task_summary['total']}",
        f"Pending: {task_summary['pending']}, In Progress: {task_summary['in_progress']}, Completed: {task_summary['completed']}",
        f"Overdue Tasks: {task_summary['overdue']}",
        f"Upcoming Tasks (Next 7 Days): {task_summary['upcoming']}",
        f"Progress: {task_summary['progress_percent']}%",
        "",
        "--- TASKS (Task ID, Title, Category, Priority, Due Date, Status) ---",
    ])

    for t in tasks_context:
        flag = " [OVERDUE]" if t["is_overdue"] else (" [UPCOMING]" if t["is_upcoming"] else "")
        lines.append(f"- ID: {t['task_id']} | {t['title']} ({t['category']}) | Priority: {t['priority']} | Due: {t['due_date']} | Status: {t['status']}{flag}")

    if not tasks_context:
        lines.append("(No tasks recorded)")

    lines.extend([
        "",
        "--- EXPENSES (Description, Category, Estimated, Actual, Status) ---",
    ])
    for e in expenses_context:
        act = f", Actual: {currency} {e['actual_amount']}" if e['actual_amount'] is not None else ""
        lines.append(f"- {e['description']} ({e['category']}): Est: {currency} {e['estimated_amount']}{act} | {e['payment_status']}")

    if not expenses_context:
        lines.append("(No expenses recorded)")

    lines.extend([
        "",
        "--- VENDORS (Name, Category, Status, Quoted Amount) ---",
    ])
    for v in vendors_context:
        q = f", Quoted: {currency} {v['quote']}" if v['quote'] else ", No quote"
        notes_str = f" | Notes: {v['notes']}" if v['notes'] else ""
        lines.append(f"- {v['name']} ({v['category']}): Status: {v['status']}{q}{notes_str}")

    if not vendors_context:
        lines.append("(No vendors recorded)")

    lines.extend([
        "",
        "--- STORED PLAN SUMMARY ---",
        f"Theme: {plan_theme}",
        f"Overview: {plan_overview}",
    ])

    raw_text = "\n".join(lines)
    rendered_text = format_untrusted_block("event_context", raw_text)

    return context_dict, rendered_text

