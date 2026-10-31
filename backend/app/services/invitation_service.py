"""
Invitation generation service for EventMate AI.
Produces culturally authentic celebration invitation text with script fidelity,
Devanagari ratio validation for Hindi, precomputed calendar dates, and demo mode.
"""

from datetime import date
import logging
import re
import time
from typing import Optional, Tuple
from fastapi import HTTPException

try:
    from app.schemas import (
        AIInvitationResponse,
        InvitationRequest,
        InvitationResponse,
    )
    from app.services.ai_service import AIService
    from app.services.prompts import INVITATION_SYSTEM_PROMPT, format_untrusted_block
    from app.services.today import get_now
except ImportError:
    from backend.app.schemas import (
        AIInvitationResponse,
        InvitationRequest,
        InvitationResponse,
    )
    from backend.app.services.ai_service import AIService
    from backend.app.services.prompts import INVITATION_SYSTEM_PROMPT, format_untrusted_block
    from backend.app.services.today import get_now

logger = logging.getLogger("eventmate.invitations")


def compute_devanagari_ratio(text: str) -> float:
    """Calculates the ratio of Devanagari Unicode characters (U+0900 to U+097F) over all alphabetic letters."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    devanagari_letters = [ch for ch in letters if "\u0900" <= ch <= "\u097f"]
    return len(devanagari_letters) / len(letters)


def validate_invitation_text(text: str, language: str) -> Tuple[bool, Optional[str]]:
    """
    Validates invitation text constraints:
    - Between 40 and 2000 characters.
    - Hindi: at least 30% Devanagari script.
    - English: at most 10% Devanagari script.
    """
    if not text or not text.strip():
        return False, "Invitation text is empty."

    clean_text = text.strip()
    if len(clean_text) < 40:
        return False, f"Invitation text is too short ({len(clean_text)} chars). Minimum 40 characters required."

    if len(clean_text) > 2000:
        return False, f"Invitation text exceeds 2000 characters ({len(clean_text)} chars)."

    ratio = compute_devanagari_ratio(clean_text)

    if language == "Hindi":
        if ratio < 0.30:
            return False, f"Hindi invitation must use authentic Devanagari script (got {ratio*100:.1f}%, minimum 30% required)."
    else:  # English
        if ratio > 0.10:
            return False, f"English invitation contains too much Devanagari text ({ratio*100:.1f}%, maximum 10% allowed)."

    return True, None


def get_demo_invitation(req: InvitationRequest, weekday: str, long_date: str) -> str:
    """Generates authentic deterministic invitation text for demo mode."""
    if req.language == "Hindi":
        if req.tone in ("Formal", "Traditional"):
            return (
                f"॥ श्री गणेशाय नमः ॥\n\n"
                f"मांगलिक आमंत्रण पत्र\n\n"
                f"सस्नेह नमस्कार। हमें यह बताते हुए अत्यंत हर्ष हो रहा है कि हमारे परिवार में "
                f"{req.event_type} का शुभ आयोजन होने जा रहा है।\n\n"
                f"आयोजक: {req.host_name}\n"
                f"शुभ दिन व दिनांक: {weekday}, {long_date}\n"
                f"समय: {req.event_time} बजे\n"
                f"स्थान: {req.location}\n\n"
                f"इस मंगल बेला पर आपकी गरिमामयी उपस्थिति एवं स्नेहमयी आशीर्वाद सादर प्रार्थनीय हैं। "
                f"आपकी उपस्थिति हमारे इस उत्सव की शोभा में चार चांद लगाएगी।\n\n"
                f"दर्शनाभिलाषी:\n{req.host_name} एवं समस्त परिवार"
            )
        else:  # Friendly / Fun / Elegant
            return (
                f"खुशियों का बुलावा!\n\n"
                f"प्यारे दोस्तों और परिवारजनों, जश्न का वक्त आ गया है! "
                f"हम अपने परिवार में {req.event_type} की एक बेहद खास और यादगार शाम मनाने जा रहे हैं।\n\n"
                f"होस्ट: {req.host_name}\n"
                f"दिन: {weekday}, {long_date}\n"
                f"समय: {req.event_time} बजे\n"
                f"स्थान: {req.location}\n\n"
                f"ढेर सारी मस्ती, लजीज दावत और सुनहरी यादों के साथ आपका इंतजार रहेगा। "
                f"कृपया समय पर पधारकर इस शाम को और भी खुशनुमा बनाएं!\n\n"
                f"स्नेही: {req.host_name}"
            )
    else:  # English
        if req.tone == "Formal":
            return (
                f"Cordially Invited\n\n"
                f"{req.host_name} requests the honor of your gracious presence at the celebration of our {req.event_type}.\n\n"
                f"Date: {weekday}, {long_date}\n"
                f"Time: {req.event_time} Hours\n"
                f"Venue: {req.location}\n\n"
                f"Your esteemed presence will add immense joy and grace to our celebrations as we mark this meaningful occasion.\n\n"
                f"Warm Regards,\n{req.host_name}"
            )
        elif req.tone in ("Friendly", "Fun"):
            return (
                f"Let's Celebrate Together!\n\n"
                f"Save the date! We are throwing a celebration for our {req.event_type} and we simply cannot celebrate without you!\n\n"
                f"Hosted by: {req.host_name}\n"
                f"When: {weekday}, {long_date} at {req.event_time}\n"
                f"Where: {req.location}\n\n"
                f"Get ready for laughter, great music, fantastic company, and delicious food. "
                f"We can't wait to see you there and make memories together!\n\n"
                f"Cheers,\n{req.host_name}"
            )
        else:  # Elegant / Traditional
            return (
                f"A Celebration of Joy\n\n"
                f"Together with our families, {req.host_name} warmly invites you to celebrate the joyous occasion of our {req.event_type}.\n\n"
                f"Date: {weekday}, {long_date}\n"
                f"Time: {req.event_time}\n"
                f"Venue: {req.location}\n\n"
                f"May this gathering be blessed with warmth, laughter, and everlasting memories. "
                f"Your presence and blessings will make our special day truly complete.\n\n"
                f"With Affection,\n{req.host_name}"
            )


def build_invitation_user_prompt(
    req: InvitationRequest,
    weekday: str,
    long_date: str,
) -> str:
    content_lines = [
        f"Event Type: {req.event_type}",
        f"Host Name: {req.host_name}",
        f"Event Date: {req.event_date.isoformat()} ({weekday}, {long_date})",
        f"Event Time: {req.event_time}",
        f"Location: {req.location}",
        f"Requested Language: {req.language}",
        f"Requested Tone: {req.tone}",
    ]
    if req.additional_instructions:
        content_lines.append(f"Additional Instructions: {req.additional_instructions}")

    content = "\n".join(content_lines)

    return (
        f"{format_untrusted_block('invitation_details', content)}\n\n"
        f"Critical Instructions:\n"
        f"1. You MUST use the exact host name '{req.host_name}', date '{weekday}, {long_date}', time '{req.event_time}', and location '{req.location}'. Do not alter them.\n"
        f"2. Write in '{req.language}' with '{req.tone}' tone.\n"
        f"3. If language is Hindi, write authentic Hindi in Devanagari script (U+0900 to U+097F). Do NOT use Latin transliteration or Roman Hindi.\n"
        f"4. Length must be between 40 and 2000 characters.\n"
        f"5. Do NOT invent RSVP links, booking portals, or external websites."
    )


async def generate_invitation(
    payload: InvitationRequest,
    ai_service: AIService,
) -> InvitationResponse:
    """Generates celebration invitation with language fidelity and script verification."""
    start_time = time.perf_counter()

    # Pre-compute weekday and long date
    weekday = payload.event_date.strftime("%A")
    long_date = payload.event_date.strftime("%d %B %Y")

    # Demo Mode
    if not ai_service.is_configured:
        demo_text = get_demo_invitation(payload, weekday, long_date)
        duration = time.perf_counter() - start_time
        logger.info(
            "generate_invitation demo path=/api/invitations/generate language=%s tone=%s duration=%.3fs outcome=200",
            payload.language,
            payload.tone,
            duration,
        )
        return InvitationResponse(
            invitation_text=demo_text,
            language=payload.language,
            tone=payload.tone,
            source="demo",
            model=None,
            generated_at=get_now(),
        )

    # Live Gemini Call
    user_prompt = build_invitation_user_prompt(payload, weekday, long_date)

    try:
        raw_output, source, model = await ai_service.generate_structured(
            system_prompt=INVITATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AIInvitationResponse,
        )
    except Exception as exc:
        duration = time.perf_counter() - start_time
        logger.error(
            "generate_invitation ai_error duration=%.3fs outcome=%s exception=%s",
            duration,
            getattr(exc, "status_code", 500),
            exc.__class__.__name__,
        )
        raise

    is_valid, error_msg = validate_invitation_text(raw_output.invitation_text, payload.language)

    # ONE repair retry on validation failure (e.g. Hindi with insufficient Devanagari)
    if not is_valid:
        logger.warning("Initial invitation text failed validation (%s), attempting repair retry...", error_msg)
        repair_prompt = (
            f"{user_prompt}\n\n"
            f"The previous output failed validation: {error_msg}\n"
            f"Please regenerate the invitation strictly following all language and script rules."
        )
        try:
            raw_output, source, model = await ai_service.generate_structured(
                system_prompt=INVITATION_SYSTEM_PROMPT,
                user_prompt=repair_prompt,
                response_model=AIInvitationResponse,
            )
            is_valid, error_msg = validate_invitation_text(raw_output.invitation_text, payload.language)
        except Exception as retry_exc:
            logger.error("Invitation repair retry failed: %s", retry_exc)
            raise HTTPException(
                status_code=502,
                detail=f"AI service produced invalid invitation text: {error_msg}",
            )

        if not is_valid:
            raise HTTPException(
                status_code=502,
                detail=f"AI service produced invalid invitation text after retry: {error_msg}",
            )

    duration = time.perf_counter() - start_time
    logger.info(
        "generate_invitation success language=%s tone=%s duration=%.3fs outcome=200",
        payload.language,
        payload.tone,
        duration,
    )

    return InvitationResponse(
        invitation_text=raw_output.invitation_text.strip(),
        language=payload.language,
        tone=payload.tone,
        source=source,
        model=model,
        generated_at=get_now(),
    )

