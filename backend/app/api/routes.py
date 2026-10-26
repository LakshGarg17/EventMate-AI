from fastapi import APIRouter, Depends
try:

    from app.config import settings
    from app.schemas import EventPlanResponse, EventRequest
    from app.services.ai_service import AIService
except ImportError:
    from backend.app.config import settings
    from backend.app.schemas import EventPlanResponse, EventRequest
    from backend.app.services.ai_service import AIService


router = APIRouter()


def get_ai_service() -> AIService:
    return AIService(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model
    )


@router.get("/health", tags=["System"])
async def health_check():
    """Returns system status and whether live Gemini AI is configured without exposing secrets."""
    return {
        "status": "ok",
        "ai_configured": settings.is_ai_configured,
        "model": settings.gemini_model if settings.is_ai_configured else "demo"
    }


@router.post("/events/generate", response_model=EventPlanResponse, tags=["Events"])
async def generate_event_plan(
    request: EventRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> EventPlanResponse:
    """Generates an end-to-end celebration and event plan using Gemini AI or demo mode."""
    return await ai_service.generate_plan(request)
