"""
Theme and decoration recommendation service for EventMate AI.
Produces culturally rich theme concepts, validates hex color palettes,
computes deterministic decoration budget estimates from shares, and provides demo fallbacks.
"""

from decimal import Decimal
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session

try:
    from app.db.models import Event
    from app.schemas import (
        AIThemeItem,
        AIThemeResponse,
        ThemePaletteColor,
        ThemeRecommendationItem,
        ThemeRecommendationRequest,
        ThemeRecommendationResponse,
    )
    from app.services.ai_service import AIService
    from app.services.currency import from_minor, to_minor, validate_and_parse_money
    from app.services.prompts import THEME_SYSTEM_PROMPT, format_untrusted_block
    from app.services.today import get_now
except ImportError:
    from backend.app.db.models import Event
    from backend.app.schemas import (
        AIThemeItem,
        AIThemeResponse,
        ThemePaletteColor,
        ThemeRecommendationItem,
        ThemeRecommendationRequest,
        ThemeRecommendationResponse,
    )
    from backend.app.services.ai_service import AIService
    from backend.app.services.currency import from_minor, to_minor, validate_and_parse_money
    from backend.app.services.prompts import THEME_SYSTEM_PROMPT, format_untrusted_block
    from backend.app.services.today import get_now

logger = logging.getLogger("eventmate.themes")

HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEMO_THEMES: Dict[str, List[Dict[str, Any]]] = {
    "Wedding": [
        {
            "name": "Royal Marigold & Terracotta Heritage",
            "description": "A magnificent royal Indian celebration featuring rich marigold florals, handcrafted brass urns, and earthen terracotta tones.",
            "color_palette": [
                {"name": "Marigold Gold", "hex": "#FFB300"},
                {"name": "Terracotta Sunset", "hex": "#C75B12"},
                {"name": "Deep Crimson", "hex": "#800020"},
                {"name": "Ivory Silk", "hex": "#FDFBF7"},
            ],
            "decoration_ideas": [
                "Cascading marigold and tuberose mandap backdrop",
                "Brass urli bowls with floating candles and rose petals",
                "Printed block-print drapes with golden tassels",
            ],
            "lighting": "Warm ambient amber wash with heritage copper lanterns and fairy light canopy",
            "venue_style": "Heritage courtyard, palatial banquet, or outdoor royal garden",
            "budget_share_percent": 20,
            "implementation_tips": [
                "Source fresh marigold chains from wholesale flower markets a day prior",
                "Use reusable brass decor items to optimize costs",
            ],
        },
        {
            "name": "Ethereal Pastel Floral & Ivory Romance",
            "description": "Soft romantic ambiance with blush peonies, delicate white hydrangeas, sage greenery, and warm ivory drapery.",
            "color_palette": [
                {"name": "Blush Rose", "hex": "#F8C8DC"},
                {"name": "Sage Green", "hex": "#A8D5BA"},
                {"name": "Warm Ivory", "hex": "#FFFDD0"},
                {"name": "Soft Lavender", "hex": "#E6E6FA"},
            ],
            "decoration_ideas": [
                "Sheer pastel chiffon ceiling draping",
                "Floral runner with eucalyptus and baby's breath",
                "Mirror-finish acrylic welcome easel with gold calligraphy",
            ],
            "lighting": "Soft candlelit glow with dimmable crystal chandelier uplighting",
            "venue_style": "Contemporary glasshouse, beachfront lawn, or minimalist ballroom",
            "budget_share_percent": 25,
            "implementation_tips": [
                "Combine silk flowers for high ceiling installations with real blooms for table runners",
            ],
        },
        {
            "name": "Midnight Starlight & Regal Champagne",
            "description": "A glamorous contemporary evening gala filled with deep navy backdrops, shimmering champagne gold, and twinkling lights.",
            "color_palette": [
                {"name": "Midnight Navy", "hex": "#0A192F"},
                {"name": "Champagne Gold", "hex": "#D4AF37"},
                {"name": "Silver Frost", "hex": "#C0C0C0"},
                {"name": "Pure Starlight", "hex": "#F8F9FA"},
            ],
            "decoration_ideas": [
                "Starry-night tunnel entryway with thousands of micro-LEDs",
                "Gold geometric centerpieces with white calla lilies",
                "Navy velvet lounge seating vignettes",
            ],
            "lighting": "Cool blue ambient perimeter wash with focused warm pin-spots on tables",
            "venue_style": "Modern luxury hotel ballroom or rooftop terrace",
            "budget_share_percent": 18,
            "implementation_tips": [
                "Focus lighting fixtures rather than heavy physical props to create dramatic scale",
            ],
        },
    ],
    "Birthday": [
        {
            "name": "Neon Pop & Electric Glow Carnival",
            "description": "High-energy, vibrant celebration featuring neon accents, geometric arches, and playful interactive photo-ops.",
            "color_palette": [
                {"name": "Electric Pink", "hex": "#FF1493"},
                {"name": "Cyber Cyan", "hex": "#00FFFF"},
                {"name": "Laser Lemon", "hex": "#FFFF00"},
                {"name": "Neon Lime", "hex": "#39FF14"},
            ],
            "decoration_ideas": [
                "Custom neon LED signage with celebrant's name or catchphrase",
                "Organic balloon garland with chrome and pastel accents",
                "Glow-in-the-dark graffiti photo backdrop wall",
            ],
            "lighting": "UV blacklights combined with programmable color-changing LED tubes",
            "venue_style": "Trendy warehouse, club venue, or modern indoor party hall",
            "budget_share_percent": 18,
            "implementation_tips": [
                "Rent LED signs rather than purchasing custom neon glass",
            ],
        },
        {
            "name": "Boho Sunset Meadow & Pampas Grass",
            "description": "Relaxed, earthy aesthetic with natural woven textures, dried florals, sun-bleached wood, and warm sunset hues.",
            "color_palette": [
                {"name": "Terracotta", "hex": "#E07A5F"},
                {"name": "Dusty Rose", "hex": "#D8A48F"},
                {"name": "Sage Herb", "hex": "#81B29A"},
                {"name": "Cream Canvas", "hex": "#F4F1DE"},
            ],
            "decoration_ideas": [
                "Fluffy pampas grass and dried palm spear centerpieces",
                "Low picnic seating with Persian rugs and Moroccan floor cushions",
                "Macrame backdrop arch with cascading neutral dried florals",
            ],
            "lighting": "Bistro festoon string lights and hurricane glass pillar candles",
            "venue_style": "Backyard garden, rustic barn, or bohemian lounge café",
            "budget_share_percent": 15,
            "implementation_tips": [
                "Dried florals can be prepared weeks ahead and gifted to guests after the party",
            ],
        },
        {
            "name": "Cosmic Galaxy & Stardust Odyssey",
            "description": "Deep immersive space theme with galaxy watercolor textures, celestial gold starbursts, and deep cosmic violet tones.",
            "color_palette": [
                {"name": "Deep Space Purple", "hex": "#2E0854"},
                {"name": "Indigo Violet", "hex": "#4B0082"},
                {"name": "Cosmic Magenta", "hex": "#9370DB"},
                {"name": "Nebula Blue", "hex": "#00BFFF"},
            ],
            "decoration_ideas": [
                "Ceiling planetarium star projector and hanging iridescent planets",
                "Metallic gold constellation place cards and star confetti",
                "Black velvet photo booth with giant crescent moon prop",
            ],
            "lighting": "Star-cluster laser projections and soft indigo uplighting",
            "venue_style": "Dark banquet hall, science museum, or rooftop space",
            "budget_share_percent": 16,
            "implementation_tips": [
                "Laser star projectors cover massive square footage at very low rental cost",
            ],
        },
    ],
    "Community Event": [
        {
            "name": "Vibrant Cultural Mela & Festive Bazaar",
            "description": "Lively open-air festive carnival with colorful regional textiles, handcrafted kites, and traditional market stalls.",
            "color_palette": [
                {"name": "Carnival Red", "hex": "#E63946"},
                {"name": "Festive Saffron", "hex": "#F4A261"},
                {"name": "Peacock Teal", "hex": "#2A9D8F"},
                {"name": "Sun Yellow", "hex": "#E9C46A"},
            ],
            "decoration_ideas": [
                "Criss-crossing colorful fabric bunting and paper lanterns overhead",
                "Festive marketplace stalls with striped fabric awnings",
                "Decorated auto-rickshaw or traditional cart photo station",
            ],
            "lighting": "Warm overhead festoon string bulbs crisscrossing the public space",
            "venue_style": "Community park, town square, school grounds, or open amphitheater",
            "budget_share_percent": 12,
            "implementation_tips": [
                "Engage local artisan volunteers to craft fabric buntings using remnant textiles",
            ],
        },
        {
            "name": "Eco-Friendly Botanical Harvest Fair",
            "description": "Sustainable and earthy community gathering emphasizing upcycled materials, potted indigenous plants, and clean greenery.",
            "color_palette": [
                {"name": "Forest Green", "hex": "#2D6A4F"},
                {"name": "Fresh Mint", "hex": "#74C69D"},
                {"name": "Natural Burlap", "hex": "#D8F3DC"},
                {"name": "Warm Bark", "hex": "#8B5A2B"},
            ],
            "decoration_ideas": [
                "Living potted plant centerpieces that can be planted after the event",
                "Signage made from reclaimed pallet wood and chalkboard paint",
                "Jute and burlap table runners with herb planters",
            ],
            "lighting": "Solar-powered LED garden stakes and warm perimeter pathway lanterns",
            "venue_style": "Community garden, civic center pavilion, or botanical green",
            "budget_share_percent": 10,
            "implementation_tips": [
                "Offer the potted plants as prizes or plant them in the community garden afterwards",
            ],
        },
        {
            "name": "Golden Jubilee Heritage & Civic Pride",
            "description": "Dignified and inspiring setup featuring stately golden crests, national civic motifs, and timeless architectural accents.",
            "color_palette": [
                {"name": "Regal Gold", "hex": "#D4AF37"},
                {"name": "Deep Ochre", "hex": "#8B0000"},
                {"name": "Classic Parchment", "hex": "#F5F5DC"},
                {"name": "Slate Navy", "hex": "#2F4F4F"},
            ],
            "decoration_ideas": [
                "Formal stage backdrop with draped velvet swags and crest",
                "Podium decorated with clean white floral spray and ceremonial flags",
                "Exhibition display boards showcasing community history milestones",
            ],
            "lighting": "Even, glare-free white stage wash with warm side spotlights",
            "venue_style": "Town hall, civic auditorium, or community heritage building",
            "budget_share_percent": 14,
            "implementation_tips": [
                "Prioritize high-visibility stage presentation and clear signage",
            ],
        },
    ],
}


def sanitize_hex_color(hex_str: str) -> Optional[str]:
    """Validates #RRGGBB format and normalizes to uppercase."""
    if not hex_str or not isinstance(hex_str, str):
        return None
    val = hex_str.strip()
    if not val.startswith("#"):
        val = f"#{val}"
    if HEX_COLOR_REGEX.match(val):
        return val.upper()
    return None


def calculate_decoration_budget(total_budget_minor: int, percent: int, currency: str) -> str:
    """Calculates estimated decoration budget: total_budget * percent / 100 with integer math."""
    clamped_pct = max(5, min(40, percent))
    dec_minor = (total_budget_minor * clamped_pct) // 100
    return from_minor(dec_minor, currency)


def validate_and_normalize_themes(
    raw_themes: List[AIThemeItem],
    total_budget_minor: int,
    currency: str,
) -> List[ThemeRecommendationItem]:
    """Validates, deduplicates, and sanitizes theme recommendations."""
    valid_items: List[ThemeRecommendationItem] = []
    seen_names: Set[str] = set()

    for item in raw_themes:
        name = item.name.strip()
        folded_name = name.casefold()
        if not name or folded_name in seen_names:
            continue

        # Sanitize color palette
        clean_colors: List[ThemePaletteColor] = []
        for c in item.color_palette or []:
            sanitized_hex = sanitize_hex_color(c.hex)
            if sanitized_hex:
                clean_colors.append(
                    ThemePaletteColor(name=c.name.strip()[:50] or "Accent", hex=sanitized_hex)
                )

        if len(clean_colors) < 3:
            # Need at least 3 valid colors
            continue

        seen_names.add(folded_name)
        clamped_pct = max(5, min(40, item.budget_share_percent))
        est_decor_budget = calculate_decoration_budget(total_budget_minor, clamped_pct, currency)

        clean_ideas = [idea.strip()[:200] for idea in (item.decoration_ideas or []) if idea.strip()][:10]
        clean_tips = [tip.strip()[:200] for tip in (item.implementation_tips or []) if tip.strip()][:10]

        valid_items.append(
            ThemeRecommendationItem(
                name=name[:100],
                description=item.description.strip()[:500],
                color_palette=clean_colors[:6],
                decoration_ideas=clean_ideas if clean_ideas else ["Creative table centerpieces", "Themed entrance arch"],
                lighting=item.lighting.strip()[:300] if item.lighting else "Ambient warm uplighting",
                venue_style=item.venue_style.strip()[:300] if item.venue_style else "Banquet hall or outdoor lawn",
                budget_share_percent=clamped_pct,
                estimated_decoration_budget=est_decor_budget,
                is_estimate=True,
                implementation_tips=clean_tips if clean_tips else ["Book floral decor early to lock in seasonal rates"],
            )
        )

        if len(valid_items) >= 5:
            break

    return valid_items


def build_theme_user_prompt(payload: ThemeRecommendationRequest, total_budget_str: str) -> str:
    parts = [
        f"Event Type: {payload.event_type}",
        f"Location: {payload.location}",
        f"Guest Count: {payload.guest_count}",
        f"Total Budget: {payload.currency} {total_budget_str}",
    ]
    if payload.venue_type:
        parts.append(f"Venue Type: {payload.venue_type}")
    if payload.preferred_style:
        parts.append(f"Preferred Style: {payload.preferred_style}")
    if payload.additional_preferences:
        parts.append(f"Additional Preferences: {payload.additional_preferences}")

    content = "\n".join(parts)
    return (
        f"{format_untrusted_block('event_details', content)}\n\n"
        f"Recommend 3 to 5 unique, stunning celebration theme concepts tailored to these parameters. "
        f"Return ONLY the requested JSON schema. Make no vendor or venue availability claims."
    )


async def recommend_themes(
    payload: ThemeRecommendationRequest,
    ai_service: AIService,
    db: Session,
) -> ThemeRecommendationResponse:
    """Generates theme recommendations with strict color validation and budget estimates."""
    start_time = time.perf_counter()

    # If event_id is supplied, verify it exists
    if payload.event_id:
        event = db.get(Event, payload.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Specified event_id not found")

    # Validate and parse total budget
    parsed_dec = validate_and_parse_money(payload.total_budget, currency=payload.currency, field_name="total_budget")
    if parsed_dec <= 0:
        raise HTTPException(status_code=422, detail="total_budget must be greater than zero")
    total_budget_minor = to_minor(parsed_dec, currency=payload.currency)
    total_budget_str = from_minor(total_budget_minor, currency=payload.currency)

    # Demo Mode
    if not ai_service.is_configured:
        demo_list = DEMO_THEMES.get(payload.event_type, DEMO_THEMES["Community Event"])
        theme_items = []
        for d in demo_list:
            pct = d["budget_share_percent"]
            theme_items.append(
                ThemeRecommendationItem(
                    name=d["name"],
                    description=d["description"],
                    color_palette=[ThemePaletteColor(**c) for c in d["color_palette"]],
                    decoration_ideas=d["decoration_ideas"],
                    lighting=d["lighting"],
                    venue_style=d["venue_style"],
                    budget_share_percent=pct,
                    estimated_decoration_budget=calculate_decoration_budget(total_budget_minor, pct, payload.currency),
                    is_estimate=True,
                    implementation_tips=d["implementation_tips"],
                )
            )

        duration = time.perf_counter() - start_time
        logger.info(
            "recommend_themes demo path=/api/themes/recommend duration=%.3fs outcome=200",
            duration,
        )
        return ThemeRecommendationResponse(
            themes=theme_items[:5],
            source="demo",
            model=None,
            generated_at=get_now(),
        )

    # Live Gemini AI Generation
    user_prompt = build_theme_user_prompt(payload, total_budget_str)

    try:
        raw_output, source, model = await ai_service.generate_structured(
            system_prompt=THEME_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AIThemeResponse,
        )
    except Exception as exc:
        duration = time.perf_counter() - start_time
        logger.error(
            "recommend_themes ai_error duration=%.3fs outcome=%s exception=%s",
            duration,
            getattr(exc, "status_code", 500),
            exc.__class__.__name__,
        )
        raise

    valid_themes = validate_and_normalize_themes(raw_output.themes, total_budget_minor, payload.currency)

    # ONE repair retry if fewer than 3 valid themes
    if len(valid_themes) < 3:
        logger.warning("Fewer than 3 valid themes generated (%d), attempting repair retry...", len(valid_themes))
        repair_user_prompt = (
            f"{user_prompt}\n\n"
            f"The previous output only contained {len(valid_themes)} valid themes. "
            f"Please regenerate exactly 3 to 5 complete, distinct themes with valid #RRGGBB hex palettes."
        )
        try:
            raw_output, source, model = await ai_service.generate_structured(
                system_prompt=THEME_SYSTEM_PROMPT,
                user_prompt=repair_user_prompt,
                response_model=AIThemeResponse,
            )
            valid_themes = validate_and_normalize_themes(raw_output.themes, total_budget_minor, payload.currency)
        except Exception as retry_exc:
            logger.error("Theme repair retry failed: %s", retry_exc)
            raise HTTPException(status_code=502, detail="AI service produced insufficient valid theme concepts.")

    if len(valid_themes) < 3:
        raise HTTPException(
            status_code=502,
            detail="AI service returned fewer than 3 valid theme concepts after retry.",
        )

    duration = time.perf_counter() - start_time
    logger.info(
        "recommend_themes success count=%d duration=%.3fs outcome=200",
        len(valid_themes),
        duration,
    )

    return ThemeRecommendationResponse(
        themes=valid_themes[:5],
        source=source,
        model=model,
        generated_at=get_now(),
    )

