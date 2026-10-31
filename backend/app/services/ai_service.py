import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from uuid import uuid4

from fastapi import HTTPException
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

try:
    from app.schemas import EventPlanResponse, EventRequest, RawAIPlan, RiskItem
    from app.services.budget import reconcile_budget
    from app.services.demo import generate_demo_plan
    from app.services.timeline import process_timeline
except ImportError:
    from backend.app.schemas import EventPlanResponse, EventRequest, RawAIPlan, RiskItem
    from backend.app.services.budget import reconcile_budget
    from backend.app.services.demo import generate_demo_plan
    from backend.app.services.timeline import process_timeline



logger = logging.getLogger(__name__)


def clean_json_text(text: str) -> str:
    """Defensively strips markdown code fences and whitespace from raw model output."""
    if not text:
        return ""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class AIService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash", timeout_seconds: float = 25.0):
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.model_name = model_name or "gemini-2.5-flash"
        self.timeout_seconds = timeout_seconds
        self._client: Optional[genai.Client] = None

        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def verify_model_availability(self) -> bool:
        """Verifies if the configured model is available in the Gemini API."""
        if not self._client:
            return False
        try:
            # Check availability using models.list
            models_pager = self._client.models.list()
            available_names = [m.name for m in models_pager]
            # Match directly or prefixed with 'models/'
            target = self.model_name
            target_prefixed = f"models/{target}" if not target.startswith("models/") else target
            target_unprefixed = target.replace("models/", "")
            return any(
                target == m or target_prefixed == m or target_unprefixed in m
                for m in available_names
            )
        except Exception as e:
            logger.warning("Could not verify model list: %s", e)
            return True  # Fallback to allow generation attempt

    def _build_prompt(self, request: EventRequest) -> str:
        return (
            f"You are an expert event planner designing a celebration plan.\n"
            f"Event Name: {request.event_name}\n"
            f"Event Type: {request.event_type}\n"
            f"Date of Event: {request.event_date.isoformat()}\n"
            f"Location: {request.location}\n"
            f"Number of Guests: {request.guest_count}\n"
            f"Total Budget: {request.currency} {request.total_budget:,}\n"
            f"Theme Preference: {request.theme or 'Curate a stunning, suitable theme'}\n"
            f"Additional Preferences: {request.additional_preferences or 'None'}\n\n"
            f"Critical Instructions:\n"
            f"1. Provide budget_items with realistic ESTIMATED amounts in {request.currency}. "
            f"Cover categories including: Venue, Catering, Decoration, Entertainment, Photography, Miscellaneous, and Contingency Reserve.\n"
            f"2. For each timeline task, provide 'days_before' as an integer representing how many days before the event the task should be completed (e.g. 60, 30, 14, 2, 0). Do NOT use calendar dates.\n"
            f"3. Provide realistic checklists, decoration suggestions, catering suggestions, entertainment ideas, vendor requirements, and risks with concrete mitigations."
        )

    def _call_gemini_sync(self, prompt: str) -> str:
        """Synchronous Gemini call designed to run inside asyncio.to_thread."""
        if not self._client:
            raise ValueError("Gemini client is not configured")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RawAIPlan,
            temperature=0.7,
        )

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            raise ValueError("Model returned an empty response or safety block")

        return response.text

    async def _retry_repair(self, original_prompt: str, bad_output: str, error_msg: str) -> RawAIPlan:
        """Attempts a single repair retry if initial model output failed Pydantic validation."""
        repair_prompt = (
            f"{original_prompt}\n\n"
            f"The previous output failed validation with error: {error_msg}\n"
            f"Previous output snippet: {bad_output[:500]}\n"
            f"Please regenerate the exact JSON strictly adhering to the schema."
        )
        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(self._call_gemini_sync, repair_prompt),
                timeout=self.timeout_seconds
            )
            cleaned = clean_json_text(text)
            return RawAIPlan.model_validate_json(cleaned)
        except Exception as retry_err:
            logger.error("Repair retry failed: %s", retry_err)
            raise HTTPException(
                status_code=502,
                detail=f"AI model produced invalid structured output: {error_msg}"
            )

    def _call_gemini_structured_sync(
        self,
        user_prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Synchronous Gemini call for arbitrary structured output schemas."""
        if not self._client:
            raise ValueError("Gemini client is not configured")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model,
            system_instruction=system_prompt if system_prompt else None,
            temperature=temperature,
        )

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )

        if not response or not response.text:
            raise ValueError("Model returned an empty response or safety block")

        return response.text

    async def _retry_repair_structured(
        self,
        user_prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        bad_output: str,
        error_msg: str,
    ) -> T:
        """Attempts a single repair retry for generic structured response schemas."""
        repair_prompt = (
            f"{user_prompt}\n\n"
            f"The previous output failed validation with error: {error_msg}\n"
            f"Previous output snippet: {bad_output[:500]}\n"
            f"Please regenerate the exact JSON strictly adhering to the schema."
        )
        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_gemini_structured_sync,
                    repair_prompt,
                    response_model,
                    system_prompt,
                ),
                timeout=self.timeout_seconds,
            )
            cleaned = clean_json_text(text)
            return response_model.model_validate_json(cleaned)
        except Exception as retry_err:
            logger.error("Structured repair retry failed: %s", retry_err)
            raise HTTPException(
                status_code=502,
                detail=f"AI model produced invalid structured output: {error_msg}",
            )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.7,
    ) -> Tuple[T, str, Optional[str]]:
        """
        Generic structured output generation via Gemini API.
        Enforces defensive fence stripping, Pydantic validation, one repair retry on invalid JSON,
        and consistent status code error mapping (504, 429/503, 502, 500).
        """
        if not self.is_configured:
            raise HTTPException(
                status_code=503,
                detail="Gemini API is not configured",
            )

        try:
            raw_text = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_gemini_structured_sync,
                    user_prompt,
                    response_model,
                    system_prompt,
                    temperature,
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Upstream AI request timed out. Please try again.",
            )
        except errors.APIError as api_err:
            err_str = str(api_err).lower()
            code = getattr(api_err, "code", None)
            if code == 429 or "resource has been exhausted" in err_str or "quota" in err_str:
                raise HTTPException(
                    status_code=429,
                    detail="AI service rate limit or quota exceeded. Please try again shortly.",
                )
            if code in (401, 403) or "api_key" in err_str or "auth" in err_str or "permission" in err_str:
                raise HTTPException(
                    status_code=502,
                    detail="AI service authentication failed. Please verify your GEMINI_API_KEY.",
                )
            if "not found" in err_str or "model" in err_str:
                raise HTTPException(
                    status_code=502,
                    detail=f"Configured Gemini model '{self.model_name}' was not found or is unavailable.",
                )
            raise HTTPException(
                status_code=502,
                detail=f"Upstream AI service error ({code or 'API'}): {str(api_err)}",
            )
        except ValueError as val_err:
            raise HTTPException(
                status_code=502,
                detail=f"AI service returned unusable output: {str(val_err)}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error calling Gemini API: %s", exc.__class__.__name__)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while communicating with the AI service.",
            )

        cleaned_json = clean_json_text(raw_text)
        try:
            validated = response_model.model_validate_json(cleaned_json)
        except Exception as parse_err:
            logger.warning("Initial structured AI output parse failed (%s), attempting repair retry...", parse_err)
            validated = await self._retry_repair_structured(
                user_prompt,
                response_model,
                system_prompt,
                raw_text,
                str(parse_err),
            )

        return validated, "gemini", self.model_name

    async def generate_plan(self, request: EventRequest) -> EventPlanResponse:
        """Generates an event plan via Gemini AI or falls back to demo mode."""
        # 1. Fallback to Demo Mode if API key is not configured
        if not self.is_configured:
            return generate_demo_plan(request)

        # 2. Build prompt and call Gemini
        prompt = self._build_prompt(request)
        try:
            raw_text = await asyncio.wait_for(
                asyncio.to_thread(self._call_gemini_sync, prompt),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Upstream AI request timed out. Please try again."
            )
        except errors.APIError as api_err:
            err_str = str(api_err).lower()
            code = getattr(api_err, "code", None)
            if code == 429 or "resource has been exhausted" in err_str or "quota" in err_str:
                raise HTTPException(
                    status_code=429,
                    detail="AI service rate limit or quota exceeded. Please try again shortly."
                )
            if code in (401, 403) or "api_key" in err_str or "auth" in err_str or "permission" in err_str:
                raise HTTPException(
                    status_code=502,
                    detail="AI service authentication failed. Please verify your GEMINI_API_KEY."
                )
            if "not found" in err_str or "model" in err_str:
                raise HTTPException(
                    status_code=502,
                    detail=f"Configured Gemini model '{self.model_name}' was not found or is unavailable."
                )
            raise HTTPException(
                status_code=502,
                detail=f"Upstream AI service error ({code or 'API'}): {str(api_err)}"
            )
        except ValueError as val_err:
            raise HTTPException(
                status_code=502,
                detail=f"AI service returned unusable output: {str(val_err)}"
            )
        except Exception as exc:
            logger.exception("Unexpected error calling Gemini API")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while communicating with the AI service."
            )

        # 3. Parse and validate JSON
        cleaned_json = clean_json_text(raw_text)
        try:
            raw_plan = RawAIPlan.model_validate_json(cleaned_json)
        except Exception as parse_err:
            logger.warning("Initial AI output parse failed (%s), attempting repair retry...", parse_err)
            raw_plan = await self._retry_repair(prompt, raw_text, str(parse_err))

        # 4. Reconcile budget deterministically
        reconciled_budget = reconcile_budget(
            total_budget=request.total_budget,
            raw_items=raw_plan.budget_items,
            event_type=request.event_type,
            currency=request.currency
        )

        # 5. Process timeline deterministically
        timeline_items, timeline_warnings = process_timeline(
            event_date=request.event_date,
            raw_timeline=raw_plan.timeline,
            event_type=request.event_type
        )

        # 6. Collate top-level warnings
        all_warnings = list(raw_plan.warnings or [])
        all_warnings.extend(timeline_warnings)

        # Convert raw risks to RiskItem
        converted_risks = [
            RiskItem(
                risk=r.risk,
                likelihood=r.likelihood if r.likelihood in ("High", "Medium", "Low") else "Medium",
                mitigation=r.mitigation
            )
            for r in raw_plan.risks
        ]

        return EventPlanResponse(
            id=str(uuid4()),
            source="gemini",
            model=self.model_name,
            generated_at=datetime.now(timezone.utc),
            event_details=request,
            overview=raw_plan.overview,
            recommended_theme=raw_plan.recommended_theme,
            budget=reconciled_budget,
            checklist=raw_plan.checklist,
            timeline=timeline_items,
            decoration_suggestions=raw_plan.decoration_suggestions,
            catering_suggestions=raw_plan.catering_suggestions,
            entertainment_suggestions=raw_plan.entertainment_suggestions,
            vendor_requirements=raw_plan.vendor_requirements,
            risks=converted_risks,
            warnings=all_warnings,
        )

