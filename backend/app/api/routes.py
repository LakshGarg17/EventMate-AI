import logging
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

try:
    from app.config import settings
    from app.db.crud import (
        build_event_detail_response,
        build_event_summary_response,
        format_expense_response,
        format_task_response,
        get_event_with_relations,
    )
    from app.db.database import get_db
    from app.db.models import BudgetCategory, Event, Expense, Task
    from app.schemas import (
        EventCreate,
        EventDetailResponse,
        EventPlanResponse,
        EventRequest,
        EventSummaryResponse,
        EventUpdate,
        ExpenseCreate,
        ExpenseResponse,
        ExpenseUpdate,
        RawAIBudgetItem,
        TaskCreate,
        TaskResponse,
        TaskUpdate,
        AssistantRequest,
        AssistantResponse,
        ProposeChangesRequest,
        ProposeChangesResponse,
        ApplyChangesRequest,
        ApplyChangesResponse,
        DiscardProposalResponse,
        ThemeRecommendationRequest,
        ThemeRecommendationResponse,
        VendorCreate,
        VendorUpdate,
        VendorResponse,
        VendorComparisonResponse,
        VENDOR_CATEGORIES,
        VENDOR_STATUSES,
        InvitationRequest,
        InvitationResponse,
    )
    from app.db.crud import format_vendor_response
    from app.db.models import BudgetCategory, Event, Expense, Task, Vendor
    from app.services.ai_service import AIService
    from app.services.assistant import process_assistant_query
    from app.services.budget import reconcile_budget
    from app.services.currency import to_minor, validate_and_parse_money
    from app.services.invitation_service import generate_invitation
    from app.services.proposals import apply_proposal, discard_proposal, propose_changes
    from app.services.rate_limiter import rate_limit_ai_endpoint
    from app.services.theme_service import recommend_themes
    from app.services.vendor_service import compute_vendor_comparison
    from app.services.today import get_now, get_today
except ImportError:
    from backend.app.config import settings
    from backend.app.db.crud import (
        build_event_detail_response,
        build_event_summary_response,
        format_expense_response,
        format_task_response,
        format_vendor_response,
        get_event_with_relations,
    )
    from backend.app.db.database import get_db
    from backend.app.db.models import BudgetCategory, Event, Expense, Task, Vendor
    from backend.app.schemas import (
        EventCreate,
        EventDetailResponse,
        EventPlanResponse,
        EventRequest,
        EventSummaryResponse,
        EventUpdate,
        ExpenseCreate,
        ExpenseResponse,
        ExpenseUpdate,
        RawAIBudgetItem,
        TaskCreate,
        TaskResponse,
        TaskUpdate,
        AssistantRequest,
        AssistantResponse,
        ProposeChangesRequest,
        ProposeChangesResponse,
        ApplyChangesRequest,
        ApplyChangesResponse,
        DiscardProposalResponse,
        ThemeRecommendationRequest,
        ThemeRecommendationResponse,
        VendorCreate,
        VendorUpdate,
        VendorResponse,
        VendorComparisonResponse,
        VENDOR_CATEGORIES,
        VENDOR_STATUSES,
        InvitationRequest,
        InvitationResponse,
    )
    from backend.app.services.ai_service import AIService
    from backend.app.services.assistant import process_assistant_query
    from backend.app.services.budget import reconcile_budget
    from backend.app.services.currency import to_minor, validate_and_parse_money
    from backend.app.services.invitation_service import generate_invitation
    from backend.app.services.proposals import apply_proposal, discard_proposal, propose_changes
    from backend.app.services.rate_limiter import rate_limit_ai_endpoint
    from backend.app.services.theme_service import recommend_themes
    from backend.app.services.vendor_service import compute_vendor_comparison
    from backend.app.services.today import get_now, get_today

logger = logging.getLogger("eventmate.routes")
router = APIRouter()


def get_ai_service() -> AIService:
    return AIService(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )


# ==========================================
# Day 1 System & Generation Endpoints
# ==========================================

@router.get("/health", tags=["System"])
async def health_check():
    """Returns system status and whether live Gemini AI is configured without exposing secrets."""
    return {
        "status": "ok",
        "ai_configured": settings.is_ai_configured,
        "model": settings.gemini_model if settings.is_ai_configured else "demo",
    }


@router.get("/health/ready", tags=["System"])
def readiness_check(db: Session = Depends(get_db)):
    """Verifies that the database is reachable and ready to serve queries."""
    try:
        db.execute(select(1))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        logger.error("API readiness check database failure: %s", type(exc).__name__)
        return Response(
            content='{"status":"degraded","database":"error"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )


@router.post(
    "/events/generate",
    response_model=EventPlanResponse,
    dependencies=[Depends(rate_limit_ai_endpoint)],
    tags=["Events"],
)
async def generate_event_plan(
    request: EventRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> EventPlanResponse:
    """Generates an end-to-end celebration and event plan using Gemini AI or demo mode."""
    return await ai_service.generate_plan(request)


# ==========================================
# Day 2 Event Endpoints (Static & Parameterized)
# ==========================================

@router.post(
    "/events",
    response_model=EventDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
) -> EventDetailResponse:
    """
    Creates and saves a new event with optional generated plan.
    Atomically creates Event, BudgetCategory rows, and Task rows in a single transaction.
    """
    # Validate and parse total budget
    try:
        parsed_budget = validate_and_parse_money(payload.total_budget, payload.currency, "total_budget")
        if parsed_budget <= 0:
            raise HTTPException(status_code=422, detail="total_budget must be greater than 0")
        total_budget_minor = to_minor(parsed_budget, payload.currency)
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))

    warnings: List[str] = []

    try:
        event = Event(
            name=payload.name,
            event_type=payload.event_type,
            event_date=payload.event_date,
            location=payload.location,
            guest_count=payload.guest_count,
            total_budget=total_budget_minor,
            currency=payload.currency,
            preferred_theme=payload.preferred_theme,
            additional_preferences=payload.additional_preferences,
            generated_plan=payload.generated_plan,
        )
        db.add(event)
        db.flush()

        if payload.generated_plan and isinstance(payload.generated_plan, dict):
            # Extract raw budget items
            plan_budget = payload.generated_plan.get("budget") or {}
            plan_items = plan_budget.get("items") or []
            raw_items: List[RawAIBudgetItem] = []

            for item in plan_items:
                cat = item.get("category")
                amt = item.get("amount", 0)
                notes = item.get("notes", "")
                if cat and str(cat).strip():
                    raw_items.append(
                        RawAIBudgetItem(
                            category=str(cat).strip(),
                            estimated_amount=int(amt or 0),
                            notes=str(notes or ""),
                        )
                    )

            contingency_amt = plan_budget.get("contingency", 0)
            if contingency_amt and int(contingency_amt) > 0:
                raw_items.append(
                    RawAIBudgetItem(
                        category="Contingency Reserve",
                        estimated_amount=int(contingency_amt),
                        notes="Contingency reserve from plan",
                    )
                )

            # Reconcile server-side to guarantee category sum equals total_budget exactly
            breakdown = reconcile_budget(
                total_budget=total_budget_minor,
                raw_items=raw_items,
                event_type=payload.event_type,
                currency=payload.currency,
            )

            # De-duplicate category names
            seen_categories = set()
            for b_item in breakdown.items:
                c_name = b_item.category.strip()
                if c_name in seen_categories:
                    continue
                seen_categories.add(c_name)
                db.add(
                    BudgetCategory(
                        event_id=event.id,
                        category_name=c_name,
                        estimated_amount=b_item.amount,
                        description=b_item.notes,
                    )
                )

            # Map timeline items to tasks with status Pending
            plan_timeline = payload.generated_plan.get("timeline") or []
            for idx, t_item in enumerate(plan_timeline):
                t_title = t_item.get("task") or t_item.get("title")
                if not t_title or not str(t_title).strip():
                    warnings.append(f"Skipped timeline item #{idx + 1} due to missing task title.")
                    continue

                due_raw = t_item.get("due_date")
                if not due_raw:
                    warnings.append(f"Skipped task '{t_title}' due to missing due date.")
                    continue

                try:
                    if isinstance(due_raw, str):
                        task_due_date = date.fromisoformat(due_raw.strip())
                    elif isinstance(due_raw, date):
                        task_due_date = due_raw
                    else:
                        raise ValueError("Invalid date type")
                except Exception:
                    warnings.append(f"Skipped task '{t_title}' due to invalid date: {due_raw}.")
                    continue

                t_cat = t_item.get("category") or "General"
                t_prio = t_item.get("priority")
                if t_prio not in ("High", "Medium", "Low"):
                    t_prio = "Medium"
                t_desc = t_item.get("description")

                db.add(
                    Task(
                        event_id=event.id,
                        title=str(t_title).strip()[:120],
                        description=t_desc,
                        category=str(t_cat).strip()[:50] or "General",
                        priority=t_prio,
                        due_date=task_due_date,
                        status="Pending",
                    )
                )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create event: %s", exc)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail="Database transaction failed while creating event.")

    saved_event = get_event_with_relations(db, event.id)
    return build_event_detail_response(saved_event, warnings=warnings)


@router.get("/events", response_model=List[EventSummaryResponse], tags=["Events"])
def list_events(db: Session = Depends(get_db)) -> List[EventSummaryResponse]:
    """Lists all event summaries, newest first, avoiding N+1 queries using selectinload."""
    stmt = (
        select(Event)
        .options(
            selectinload(Event.budget_categories),
            selectinload(Event.expenses),
            selectinload(Event.tasks),
        )
        .order_by(Event.created_at.desc())
    )
    events = db.scalars(stmt).all()
    today = get_today()
    return [build_event_summary_response(ev, today=today) for ev in events]


@router.get("/events/{event_id}", response_model=EventDetailResponse, tags=["Events"])
def get_event(event_id: str, db: Session = Depends(get_db)) -> EventDetailResponse:
    """Returns full event details with budget categories, tasks, expenses, and computed summaries."""
    event = get_event_with_relations(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return build_event_detail_response(event)


@router.put("/events/{event_id}", response_model=EventDetailResponse, tags=["Events"])
def update_event(
    event_id: str,
    payload: EventUpdate,
    db: Session = Depends(get_db),
) -> EventDetailResponse:
    """
    Updates editable fields of an event.
    Rejects currency changes if expenses or categories exist (422).
    Does not rescale existing categories or duplicate tasks.
    """
    event = get_event_with_relations(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Check currency immutability if records exist
    if "currency" in update_data and update_data["currency"] != event.currency:
        if (event.budget_categories and len(event.budget_categories) > 0) or (event.expenses and len(event.expenses) > 0):
            raise HTTPException(
                status_code=422,
                detail="Cannot change currency when budget categories or expenses exist.",
            )
        event.currency = update_data["currency"]

    if "total_budget" in update_data:
        try:
            parsed_budget = validate_and_parse_money(update_data["total_budget"], event.currency, "total_budget")
            if parsed_budget <= 0:
                raise HTTPException(status_code=422, detail="total_budget must be greater than 0")
            event.total_budget = to_minor(parsed_budget, event.currency)
        except ValueError as err:
            raise HTTPException(status_code=422, detail=str(err))

    if "name" in update_data:
        event.name = update_data["name"]
    if "event_type" in update_data:
        event.event_type = update_data["event_type"]
    if "event_date" in update_data:
        event.event_date = update_data["event_date"]
    if "location" in update_data:
        event.location = update_data["location"]
    if "guest_count" in update_data:
        event.guest_count = update_data["guest_count"]
    if "preferred_theme" in update_data:
        event.preferred_theme = update_data["preferred_theme"]
    if "additional_preferences" in update_data:
        event.additional_preferences = update_data["additional_preferences"]

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update event %s: %s", event_id, exc)
        raise HTTPException(status_code=500, detail="Database transaction failed while updating event.")

    updated_event = get_event_with_relations(db, event_id)
    return build_event_detail_response(updated_event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Events"])
def delete_event(event_id: str, db: Session = Depends(get_db)):
    """Deletes the event and all cascaded child records (categories, expenses, tasks)."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        db.delete(event)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete event %s: %s", event_id, exc)
        raise HTTPException(status_code=500, detail="Database transaction failed while deleting event.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================
# Day 2 Expenses Endpoints
# ==========================================

@router.post(
    "/events/{event_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Expenses"],
)
def create_expense(
    event_id: str,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    """Creates a new expense item for an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if payload.budget_category_id:
        category = db.get(BudgetCategory, payload.budget_category_id)
        if not category or category.event_id != event_id:
            raise HTTPException(
                status_code=422,
                detail="budget_category_id must belong to the same event.",
            )

    try:
        est_dec = validate_and_parse_money(payload.estimated_amount, event.currency, "estimated_amount")
        est_minor = to_minor(est_dec, event.currency)

        act_minor = None
        if payload.actual_amount is not None:
            act_dec = validate_and_parse_money(payload.actual_amount, event.currency, "actual_amount")
            act_minor = to_minor(act_dec, event.currency)
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))

    expense = Expense(
        event_id=event.id,
        budget_category_id=payload.budget_category_id,
        description=payload.description,
        estimated_amount=est_minor,
        actual_amount=act_minor,
        payment_status=payload.payment_status,
        expense_date=payload.expense_date,
        notes=payload.notes,
    )

    try:
        db.add(expense)
        db.commit()
        db.refresh(expense)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create expense: %s", exc)
        raise HTTPException(status_code=500, detail="Database error while creating expense.")

    return format_expense_response(expense, event.currency)


@router.get("/events/{event_id}/expenses", response_model=List[ExpenseResponse], tags=["Expenses"])
def list_expenses(event_id: str, db: Session = Depends(get_db)) -> List[ExpenseResponse]:
    """Lists all expenses for an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(Expense).where(Expense.event_id == event_id).order_by(Expense.created_at.asc())
    expenses = db.scalars(stmt).all()
    return [format_expense_response(e, event.currency) for e in expenses]


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse, tags=["Expenses"])
def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    """Updates an existing expense."""
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    event = db.get(Event, expense.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Associated event not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "budget_category_id" in update_data:
        cat_id = update_data["budget_category_id"]
        if cat_id is not None:
            category = db.get(BudgetCategory, cat_id)
            if not category or category.event_id != expense.event_id:
                raise HTTPException(
                    status_code=422,
                    detail="budget_category_id must belong to the same event.",
                )
        expense.budget_category_id = cat_id

    try:
        if "estimated_amount" in update_data:
            est_dec = validate_and_parse_money(update_data["estimated_amount"], event.currency, "estimated_amount")
            expense.estimated_amount = to_minor(est_dec, event.currency)

        if "actual_amount" in update_data:
            act_val = update_data["actual_amount"]
            if act_val is not None:
                act_dec = validate_and_parse_money(act_val, event.currency, "actual_amount")
                expense.actual_amount = to_minor(act_dec, event.currency)
            else:
                expense.actual_amount = None
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))

    if "description" in update_data:
        expense.description = update_data["description"]
    if "payment_status" in update_data:
        expense.payment_status = update_data["payment_status"]
    if "expense_date" in update_data:
        expense.expense_date = update_data["expense_date"]
    if "notes" in update_data:
        expense.notes = update_data["notes"]

    try:
        db.commit()
        db.refresh(expense)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update expense %s: %s", expense_id, exc)
        raise HTTPException(status_code=500, detail="Database error while updating expense.")

    return format_expense_response(expense, event.currency)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Expenses"])
def delete_expense(expense_id: str, db: Session = Depends(get_db)):
    """Deletes an expense item."""
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    try:
        db.delete(expense)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete expense %s: %s", expense_id, exc)
        raise HTTPException(status_code=500, detail="Database error while deleting expense.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================
# Day 2 Tasks Endpoints
# ==========================================

@router.post(
    "/events/{event_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
)
def create_task(
    event_id: str,
    payload: TaskCreate,
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Creates a new task for an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    task = Task(
        event_id=event.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        due_date=payload.due_date,
        status=payload.status,
    )

    try:
        db.add(task)
        db.commit()
        db.refresh(task)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create task: %s", exc)
        raise HTTPException(status_code=500, detail="Database error while creating task.")

    return format_task_response(task, event.event_date)


@router.get("/events/{event_id}/tasks", response_model=List[TaskResponse], tags=["Tasks"])
def list_tasks(
    event_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> List[TaskResponse]:
    """Lists tasks for an event with an optional status filter."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(Task).where(Task.event_id == event_id)
    if status_filter is not None:
        if status_filter not in ("Pending", "In Progress", "Completed"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status filter '{status_filter}'. Must be Pending, In Progress, or Completed.",
            )
        stmt = stmt.where(Task.status == status_filter)

    stmt = stmt.order_by(Task.due_date.asc(), Task.created_at.asc())
    tasks = db.scalars(stmt).all()
    today = get_today()
    return [format_task_response(t, event.event_date, today=today) for t in tasks]


@router.put("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Updates an existing task in place."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    event = db.get(Event, task.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Associated event not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "title" in update_data:
        task.title = update_data["title"]
    if "description" in update_data:
        task.description = update_data["description"]
    if "category" in update_data:
        task.category = update_data["category"]
    if "priority" in update_data:
        task.priority = update_data["priority"]
    if "due_date" in update_data:
        task.due_date = update_data["due_date"]
    if "status" in update_data:
        task.status = update_data["status"]

    try:
        db.commit()
        db.refresh(task)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update task %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Database error while updating task.")

    return format_task_response(task, event.event_date)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Deletes a task."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        db.delete(task)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete task %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Database error while deleting task.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================
# Day 3 AI Assistant (Ask Mode)
# ==========================================

@router.post(
    "/events/{event_id}/assistant",
    response_model=AssistantResponse,
    dependencies=[Depends(rate_limit_ai_endpoint)],
    tags=["Assistant"],
)
async def ask_assistant(
    event_id: str,
    payload: AssistantRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> AssistantResponse:
    """
    Context-aware AI assistant endpoint (Ask mode).
    Answers questions using only current event context, budgets, tasks, and expenses.
    Does not modify database records.
    """
    return await process_assistant_query(event_id, payload, ai_service, db=db)


# ==========================================
# Day 3 Safe Plan Modification (Propose & Apply)
# ==========================================

@router.post(
    "/events/{event_id}/assistant/propose-changes",
    response_model=ProposeChangesResponse,
    dependencies=[Depends(rate_limit_ai_endpoint)],
    tags=["Assistant Proposals"],
)
async def propose_event_changes(
    event_id: str,
    payload: ProposeChangesRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> ProposeChangesResponse:
    """
    Proposes structured modifications to budget allocations or tasks.
    Deterministic backend validation previews before/after state.
    Does not modify event records.
    """
    return await propose_changes(event_id, payload.message, ai_service, db=db)


@router.post(
    "/events/{event_id}/assistant/apply-changes",
    response_model=ApplyChangesResponse,
    tags=["Assistant Proposals"],
)
def apply_event_changes(
    event_id: str,
    payload: ApplyChangesRequest,
    db: Session = Depends(get_db),
) -> ApplyChangesResponse:
    """
    Applies a previously validated and pending proposal in one atomic transaction.
    Requires confirm: true and matching state fingerprint.
    """
    return apply_proposal(event_id, payload.proposal_id, db=db)


@router.post(
    "/events/{event_id}/assistant/proposals/{proposal_id}/discard",
    response_model=DiscardProposalResponse,
    tags=["Assistant Proposals"],
)
def discard_event_proposal(
    event_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
) -> DiscardProposalResponse:
    """Discards a pending change proposal."""
    return discard_proposal(event_id, proposal_id, db=db)


# ==========================================
# Day 3 Theme & Decoration Recommendations
# ==========================================

@router.post(
    "/themes/recommend",
    response_model=ThemeRecommendationResponse,
    dependencies=[Depends(rate_limit_ai_endpoint)],
    tags=["Creative Styling"],
)
async def recommend_event_themes(
    payload: ThemeRecommendationRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> ThemeRecommendationResponse:
    """
    Stateless theme and decoration concept recommendation endpoint.
    Returns 3 to 5 curated theme concepts with hex color swatches and estimated decoration budgets.
    """
    return await recommend_themes(payload, ai_service, db=db)


# ==========================================
# Day 3 Vendor Management & Comparison
# ==========================================

@router.post(
    "/events/{event_id}/vendors",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Vendors"],
)
def create_vendor(
    event_id: str,
    payload: VendorCreate,
    db: Session = Depends(get_db),
) -> VendorResponse:
    """Creates a new vendor item for an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    quoted_minor = None
    if payload.quoted_amount is not None:
        dec = validate_and_parse_money(
            payload.quoted_amount,
            currency=event.currency,
            field_name="quoted_amount",
        )
        quoted_minor = to_minor(dec, currency=event.currency)

    now = get_now()
    vendor = Vendor(
        event_id=event_id,
        name=payload.name,
        category=payload.category,
        contact_info=payload.contact_info,
        quoted_amount=quoted_minor,
        notes=payload.notes,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create vendor: %s", exc)
        raise HTTPException(status_code=500, detail="Database error while creating vendor.")

    return format_vendor_response(vendor, event.currency)


@router.get(
    "/events/{event_id}/vendors",
    response_model=List[VendorResponse],
    tags=["Vendors"],
)
def list_vendors(
    event_id: str,
    category_filter: Optional[str] = Query(None, alias="category"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> List[VendorResponse]:
    """Lists vendors for an event with optional category and status filters."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(Vendor).where(Vendor.event_id == event_id)

    if category_filter is not None:
        if category_filter not in VENDOR_CATEGORIES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category filter '{category_filter}'. Allowed: {', '.join(VENDOR_CATEGORIES)}",
            )
        stmt = stmt.where(Vendor.category == category_filter)

    if status_filter is not None:
        if status_filter not in VENDOR_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status filter '{status_filter}'. Allowed: {', '.join(VENDOR_STATUSES)}",
            )
        stmt = stmt.where(Vendor.status == status_filter)

    stmt = stmt.order_by(Vendor.created_at.asc())
    vendors = db.scalars(stmt).all()
    return [format_vendor_response(v, event.currency) for v in vendors]


@router.get(
    "/events/{event_id}/vendors/comparison",
    response_model=VendorComparisonResponse,
    tags=["Vendors"],
)
def get_vendor_comparison(
    event_id: str,
    db: Session = Depends(get_db),
) -> VendorComparisonResponse:
    """Computes vendor quotes comparison grouped by category."""
    event = get_event_with_relations(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return compute_vendor_comparison(event)


@router.put(
    "/vendors/{vendor_id}",
    response_model=VendorResponse,
    tags=["Vendors"],
)
def update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
) -> VendorResponse:
    """Updates an existing vendor in place."""
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    event = db.get(Event, vendor.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Associated event not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        vendor.name = update_data["name"]
    if "category" in update_data:
        vendor.category = update_data["category"]
    if "contact_info" in update_data:
        vendor.contact_info = update_data["contact_info"]
    if "notes" in update_data:
        vendor.notes = update_data["notes"]
    if "status" in update_data:
        vendor.status = update_data["status"]
    if "quoted_amount" in update_data:
        raw_val = update_data["quoted_amount"]
        if raw_val is None:
            vendor.quoted_amount = None
        else:
            dec = validate_and_parse_money(
                raw_val,
                currency=event.currency,
                field_name="quoted_amount",
            )
            vendor.quoted_amount = to_minor(dec, currency=event.currency)

    vendor.updated_at = get_now()

    try:
        db.commit()
        db.refresh(vendor)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update vendor %s: %s", vendor_id, exc)
        raise HTTPException(status_code=500, detail="Database error while updating vendor.")

    return format_vendor_response(vendor, event.currency)


@router.delete(
    "/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Vendors"],
)
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
):
    """Deletes a vendor."""
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    try:
        db.delete(vendor)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete vendor %s: %s", vendor_id, exc)
        raise HTTPException(status_code=500, detail="Database error while deleting vendor.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================
# Day 3 Invitation Generator
# ==========================================

@router.post(
    "/invitations/generate",
    response_model=InvitationResponse,
    dependencies=[Depends(rate_limit_ai_endpoint)],
    tags=["Invitations"],
)
async def generate_celebration_invitation(
    payload: InvitationRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> InvitationResponse:
    """
    Stateless invitation copywriting generator.
    Produces authentic celebration invitations in English or authentic Devanagari Hindi.
    """
    return await generate_invitation(payload, ai_service)
