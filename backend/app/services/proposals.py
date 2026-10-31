"""
Safe plan modification service (propose, preview, confirm, apply, discard).
Ensures atomic execution, optimistic concurrency via SHA-256 state fingerprints,
TTL-based expiration, and repair retries on model errors.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session

try:
    from app.config import settings
    from app.db.crud import (
        build_event_detail_response,
        format_category_response,
        format_task_response,
        get_event_with_relations,
    )
    from app.db.models import BudgetCategory, ChangeProposal, Event, Task
    from app.schemas import (
        AIProposalResponse,
        ApplyChangesResponse,
        DiscardProposalResponse,
        ProposalDetail,
        ProposalPreview,
        ProposeChangesResponse,
    )
    from app.services.ai_service import AIService
    from app.services.event_context import build_event_context
    from app.services.prompts import PROPOSAL_SYSTEM_PROMPT, format_untrusted_block
    from app.services.proposal_validator import validate_proposal
    from app.services.today import get_now, get_today
except ImportError:
    from backend.app.config import settings
    from backend.app.db.crud import (
        build_event_detail_response,
        format_category_response,
        format_task_response,
        get_event_with_relations,
    )
    from backend.app.db.models import BudgetCategory, ChangeProposal, Event, Task
    from backend.app.schemas import (
        AIProposalResponse,
        ApplyChangesResponse,
        DiscardProposalResponse,
        ProposalDetail,
        ProposalPreview,
        ProposeChangesResponse,
    )
    from backend.app.services.ai_service import AIService
    from backend.app.services.event_context import build_event_context
    from backend.app.services.prompts import PROPOSAL_SYSTEM_PROMPT, format_untrusted_block
    from backend.app.services.proposal_validator import validate_proposal
    from backend.app.services.today import get_now, get_today

logger = logging.getLogger("eventmate.proposals")


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime is offset-aware in UTC for safe comparisons against SQLite timestamps."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_event_fingerprint(event: Event) -> str:
    """Computes a SHA-256 fingerprint over total budget, categories, and tasks."""
    parts = [f"total:{event.total_budget}"]
    for c in sorted(event.budget_categories or [], key=lambda c: c.id):
        parts.append(f"cat:{c.id}:{c.estimated_amount}")
    for t in sorted(event.tasks or [], key=lambda t: t.id):
        parts.append(f"task:{t.id}:{t.due_date.isoformat()}:{t.priority}")
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_proposal_user_prompt(rendered_context: str, message: str) -> str:
    return (
        f"{rendered_context}\n\n"
        f"{format_untrusted_block('user_message', message[:2000])}\n\n"
        f"Instructions:\n"
        f"1. Generate a structured proposal matching the user's modification request.\n"
        f"2. Use DELTAS for budget adjustments (e.g. '+10000', '-10000') on existing categories.\n"
        f"3. If details are missing or ambiguous, ask in `clarification_question` and leave changes empty.\n"
        f"4. Adhere strictly to category names and timeline constraints."
    )


async def propose_changes(
    event_id: str,
    message: str,
    ai_service: AIService,
    db: Session,
) -> ProposeChangesResponse:
    """Generates and previews safe plan modifications without modifying database records."""
    start_time = time.perf_counter()

    # Rule: Demo mode returns 503
    if not ai_service.is_configured:
        logger.warning(
            "propose_changes demo_mode path=/api/events/%s/assistant/propose-changes outcome=503",
            event_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Plan modification requires a configured Gemini API key.",
        )

    event = get_event_with_relations(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    context_result = build_event_context(event_id, db=db)
    if not context_result:
        raise HTTPException(status_code=404, detail="Event not found")

    _, rendered_context = context_result
    db.rollback()  # Close read transaction before async Gemini call

    user_prompt = build_proposal_user_prompt(rendered_context, message)
    today = get_today()

    try:
        raw_output, _, _ = await ai_service.generate_structured(
            system_prompt=PROPOSAL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AIProposalResponse,
        )
    except Exception as exc:
        duration = time.perf_counter() - start_time
        logger.error(
            "propose_changes ai_error event_id=%s duration=%.3fs outcome=%s exception=%s",
            event_id,
            duration,
            getattr(exc, "status_code", 500),
            exc.__class__.__name__,
        )
        raise

    # Check clarification path
    has_raw_changes = bool(
        raw_output.budget_adjustments
        or raw_output.tasks_to_add
        or raw_output.tasks_to_update
        or raw_output.new_total_budget
    )

    if raw_output.clarification_question and not has_raw_changes:
        duration = time.perf_counter() - start_time
        logger.info(
            "propose_changes clarification event_id=%s duration=%.3fs outcome=200",
            event_id,
            duration,
        )
        return ProposeChangesResponse(
            proposal=None,
            clarification=raw_output.clarification_question,
        )

    # Validate proposal deterministically
    event = get_event_with_relations(db, event_id)
    norm_changes, preview_dict, warnings, val_error = validate_proposal(event, raw_output, today)

    # ONE Automatic repair retry if validation failed
    if val_error is not None:
        logger.warning("Initial proposal validation failed (%s), attempting repair retry...", val_error)
        valid_cats = ", ".join(f"'{c.category_name}'" for c in event.budget_categories)
        repair_user_prompt = (
            f"{user_prompt}\n\n"
            f"The previous proposal failed validation with error: {val_error}\n"
            f"Valid category names for this event are: {valid_cats}\n"
            f"Please regenerate the proposal strictly correcting this error."
        )
        try:
            raw_output, _, _ = await ai_service.generate_structured(
                system_prompt=PROPOSAL_SYSTEM_PROMPT,
                user_prompt=repair_user_prompt,
                response_model=AIProposalResponse,
            )
            if raw_output.clarification_question and not (
                raw_output.budget_adjustments or raw_output.tasks_to_add or raw_output.tasks_to_update or raw_output.new_total_budget
            ):
                return ProposeChangesResponse(proposal=None, clarification=raw_output.clarification_question)

            norm_changes, preview_dict, warnings, val_error = validate_proposal(event, raw_output, today)
        except Exception as retry_exc:
            logger.error("Proposal repair retry call failed: %s", retry_exc)
            raise HTTPException(
                status_code=422,
                detail=f"Plan modification failed validation: {val_error}",
            )

        if val_error is not None:
            raise HTTPException(
                status_code=422,
                detail=f"Plan modification failed validation: {val_error}",
            )

    # Valid proposal: insert ChangeProposal row
    now = get_now()
    ttl_minutes = getattr(settings, "proposal_ttl_minutes", 30)
    expires_at = now + timedelta(minutes=ttl_minutes)
    fingerprint = compute_event_fingerprint(event)

    proposal = ChangeProposal(
        id=str(uuid4()),
        event_id=event_id,
        status="pending",
        user_message=message[:2000],
        summary=raw_output.summary[:2000] if raw_output.summary else "Plan modification proposal",
        changes=norm_changes,
        preview=preview_dict,
        base_fingerprint=fingerprint,
        created_at=now,
        expires_at=expires_at,
    )

    try:
        db.add(proposal)
        db.commit()
        db.refresh(proposal)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist change proposal: %s", exc)
        raise HTTPException(status_code=500, detail="Database error while saving proposal.")

    duration = time.perf_counter() - start_time
    logger.info(
        "propose_changes success event_id=%s proposal_id=%s duration=%.3fs outcome=200",
        event_id,
        proposal.id,
        duration,
    )

    return ProposeChangesResponse(
        proposal=ProposalDetail(
            proposal_id=proposal.id,
            summary=proposal.summary,
            preview=ProposalPreview(**preview_dict),
            warnings=warnings,
            expires_at=expires_at,
        ),
        clarification=None,
    )


def apply_proposal(
    event_id: str,
    proposal_id: str,
    db: Session,
) -> ApplyChangesResponse:
    """Applies a pending plan modification proposal in a single atomic transaction."""
    proposal = db.get(ChangeProposal, proposal_id)
    if not proposal or proposal.event_id != event_id:
        raise HTTPException(status_code=404, detail="Proposal not found for this event")

    if proposal.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Proposal is already {proposal.status}. Please request a new proposal.",
        )

    now = get_now()
    if ensure_utc(now) >= ensure_utc(proposal.expires_at):
        proposal.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Proposal has expired. Please request a new proposal.",
        )

    event = get_event_with_relations(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    current_fingerprint = compute_event_fingerprint(event)
    if current_fingerprint != proposal.base_fingerprint:
        raise HTTPException(
            status_code=409,
            detail="Event data has been modified since this proposal was created (stale proposal). Please request a new proposal.",
        )

    # Apply changes in ONE atomic transaction
    changes = proposal.changes
    try:
        # 1. Total budget update
        if changes.get("new_total_budget_minor") is not None:
            event.total_budget = changes["new_total_budget_minor"]

        # 2. Update category amounts in place (never delete/recreate rows)
        for cd in changes.get("category_deltas", []):
            cat = db.get(BudgetCategory, cd["category_id"])
            if cat:
                cat.estimated_amount = cd["new_amount_minor"]

        # 3. Add new tasks
        for t_add in changes.get("tasks_to_add", []):
            new_task = Task(
                event_id=event_id,
                title=t_add["title"],
                description=t_add.get("description"),
                category=t_add["category"],
                priority=t_add["priority"],
                due_date=date.fromisoformat(t_add["due_date"]),
                status="Pending",
            )
            db.add(new_task)

        # 4. Update existing tasks in place
        for t_up in changes.get("tasks_to_update", []):
            task_row = db.get(Task, t_up["task_id"])
            if task_row:
                if t_up.get("priority"):
                    task_row.priority = t_up["priority"]
                if t_up.get("due_date"):
                    task_row.due_date = date.fromisoformat(t_up["due_date"])
                task_row.updated_at = now

        event.updated_at = now
        proposal.status = "applied"
        proposal.applied_at = now

        db.commit()
        db.refresh(event)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to apply proposal %s: %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Database transaction failed while applying proposal.")

    # Refresh full event detail for response
    full_event = get_event_with_relations(db, event_id)
    detail = build_event_detail_response(full_event, today=get_today())

    return ApplyChangesResponse(
        proposal_id=proposal.id,
        status="applied",
        message="Plan modifications successfully applied.",
        budget_summary=detail.budget_summary,
        task_summary=detail.task_summary,
        categories=detail.budget_categories,
        tasks=detail.tasks,
    )


def discard_proposal(
    event_id: str,
    proposal_id: str,
    db: Session,
) -> DiscardProposalResponse:
    """Discards a pending change proposal."""
    proposal = db.get(ChangeProposal, proposal_id)
    if not proposal or proposal.event_id != event_id:
        raise HTTPException(status_code=404, detail="Proposal not found for this event")

    if proposal.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot discard proposal with status '{proposal.status}'.",
        )

    proposal.status = "discarded"
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to discard proposal: %s", exc)
        raise HTTPException(status_code=500, detail="Database error while discarding proposal.")

    return DiscardProposalResponse(
        proposal_id=proposal.id,
        status="discarded",
    )
