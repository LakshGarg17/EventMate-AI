from datetime import datetime, timezone
from uuid import uuid4

try:
    from app.schemas import (
        EventPlanResponse,
        EventRequest,
        RawAIBudgetItem,
        RawAITimelineItem,
        RiskItem,
        ThemeInfo,
    )
    from app.services.budget import reconcile_budget
    from app.services.timeline import process_timeline
except ImportError:
    from backend.app.schemas import (
        EventPlanResponse,
        EventRequest,
        RawAIBudgetItem,
        RawAITimelineItem,
        RiskItem,
        ThemeInfo,
    )
    from backend.app.services.budget import reconcile_budget
    from backend.app.services.timeline import process_timeline



DEMO_THEMES = {
    "Wedding": {
        "name": "Elegance & Blooms",
        "description": "Timeless romantic aesthetic featuring soft ambient lighting, lush floral arches, and ivory-gold accents.",
        "color_palette": ["#F8F9FA", "#E9D8A6", "#EE9B00", "#005F73", "#0A9396"],
        "decorations": [
            "Lush floral arch with seasonal white and pastel blossoms",
            "Fairy light canopy with warm Edison string bulbs",
            "Custom gold foil welcome signage with personalized calligraphy",
            "Fabric-draped backdrop behind the main ceremonial stage",
            "Elegant crystal candelabra centerpieces on guest tables",
        ],
        "catering": [
            "Welcome cocktail bar featuring handcrafted botanical mocktails",
            "Multi-course gourmet seated dining with regional culinary highlights",
            "Artisanal dessert spread with 3-tier celebration cake",
            "Late-night comfort snack corner (gourmet sliders and chai)",
        ],
        "entertainment": [
            "Acoustic string quartet during welcome reception and vows",
            "Live high-energy dance band or premier DJ for evening reception",
            "Curated couple spotlight dance with indoor cold-spark fountain effects",
            "Interactive digital guestbook photo kiosk",
        ],
        "vendors": [
            "Premier banquet venue or heritage lawn with full power backup",
            "Full-service catering team with dedicated floor captain",
            "Cinematic wedding videographer & candid lead photographer",
            "Event lighting & professional sound technician",
            "Bridal makeup artist & hair stylist crew",
        ],
        "risks": [
            RiskItem(
                risk="Inclement weather or outdoor temperature fluctuations",
                likelihood="Medium",
                mitigation="Book venue with indoor backup hall or secure waterproof canopy tents with climate control."
            ),
            RiskItem(
                risk="Vendor arrival delays in peak city traffic",
                likelihood="Medium",
                mitigation="Contractually mandate vendor load-in at least 4 hours prior to guest arrival."
            ),
            RiskItem(
                risk="Guest count overruns exceeding banquet capacity",
                likelihood="Low",
                mitigation="Mandate digital RSVP confirmation 10 days in advance and keep a 10% banquet buffer."
            ),
        ],
        "checklist": [
            "Finalize guest list and issue formal invitations",
            "Confirm deposit with primary venue and key vendors",
            "Schedule catering menu tasting and dietary restriction review",
            "Approve floor plan and seating arrangements",
            "Finalize sound check and lighting cue sheet",
            "Assemble emergency wedding day bridal kit",
        ],
    },
    "Birthday": {
        "name": "Vibrant Celebration",
        "description": "Dynamic, joyful, and contemporary celebration with playful color pops and memorable interactive entertainment.",
        "color_palette": ["#FF6B6B", "#4ECDC4", "#FFE66D", "#1A535C", "#F7FFF7"],
        "decorations": [
            "Organic organic balloon garland arch at entrance with metallic accents",
            "Custom neon signage with honoree's name or milestone milestone tagline",
            "Themed photo backdrop with personalized props and ring light",
            "Coordinated tableware and color-themed table runners",
            "Custom LED uplighting highlighting the party area",
        ],
        "catering": [
            "Crowd-pleasing live food counters (street food / tacos / pizza)",
            "Signature designer birthday cake tailored to recipient's passions",
            "Custom cupcake and dessert station with personalized toppers",
            "Signature mocktail and fruit spritzer refreshment bar",
        ],
        "entertainment": [
            "Dynamic emcee or party entertainer running group trivia and party games",
            "High-energy DJ with custom playlist of honoree's favorite decades",
            "Instant Polaroid photo booth with magnetic takeaway sleeves",
            "Surprise slideshow or video tribute from close family and friends",
        ],
        "vendors": [
            "Party lounge venue, rooftop, or private hall",
            "Artisanal specialty baker for customized centerpiece cake",
            "Party decorator specializing in balloon installations and neon lights",
            "Event photographer for candid party coverage",
            "Sound system and DJ service provider",
        ],
        "risks": [
            RiskItem(
                risk="Catering quantity shortfall due to last-minute plus-ones",
                likelihood="Medium",
                mitigation="Plan catering with a 15% headcount buffer and quick replenishment options."
            ),
            RiskItem(
                risk="Noise complaints or venue curfew constraints",
                likelihood="High",
                mitigation="Review venue sound guidelines in advance and transition to indoor lounge past 10 PM."
            ),
            RiskItem(
                risk="Cake delivery mishap or melting in warm weather",
                likelihood="Low",
                mitigation="Schedule delivery 2 hours prior with on-site refrigeration confirmed."
            ),
        ],
        "checklist": [
            "Select theme and book celebration venue",
            "Send electronic invitations and collect dietary notes",
            "Order custom cake and finalize food menu",
            "Purchase decoration items and party favors",
            "Prepare party playlist and game prizes",
            "Confirm timing with photographer and entertainer",
        ],
    },
    "Community Event": {
        "name": "Civic Unity & Harmony",
        "description": "Accessible, engaging community gathering promoting togetherness, cultural appreciation, and local engagement.",
        "color_palette": ["#2B2D42", "#8D99AE", "#EDF2F4", "#EF233C", "#D90429"],
        "decorations": [
            "Welcoming branded banners and clear directional signage",
            "Eco-friendly bunting and recyclable festive decor",
            "Well-lit stage with community banner backdrop",
            "Accessible registration and information welcome desks",
            "Information kiosk boards for community announcements",
        ],
        "catering": [
            "Community buffet or food truck village with diverse dietary choices",
            "Beverage station with water refill dispensers and herbal teas",
            "Boxed refreshment packages for volunteers and keynote contributors",
            "Finger foods and fresh fruit platters for easy mingling",
        ],
        "entertainment": [
            "Local community performers, student choir, and cultural showcase",
            "Keynote addresses and interactive town-hall panel discussion",
            "Children's activity corner with face-painting and lawn games",
            "Community raffle or awards recognition segment",
        ],
        "vendors": [
            "Public auditorium, sports ground, or community center",
            "Commercial audiovisual provider (mics, monitors, PA speakers, projector)",
            "Sanitation and event security personnel",
            "Local catering or vetted food truck partners",
            "First aid and paramedic emergency responder presence",
        ],
        "risks": [
            RiskItem(
                risk="Unregistered crowd turnout exceeding facility capacity",
                likelihood="Medium",
                mitigation="Utilize free pre-registration ticketing and enforce security capacity limits at gates."
            ),
            RiskItem(
                risk="Audio feedback or microphone failure during key speeches",
                likelihood="Medium",
                mitigation="Require an on-site AV technician and conduct full acoustic check 2 hours prior."
            ),
            RiskItem(
                risk="Medical emergency or heat exhaustion among attendees",
                likelihood="Low",
                mitigation="Designate an air-conditioned first-aid station staffed with certified volunteers."
            ),
        ],
        "checklist": [
            "Secure municipal event permits and insurance coverage",
            "Launch community promotional flyer campaign",
            "Recruit and orient volunteer leads for crowd direction",
            "Conduct safety, accessibility, and sanitation review",
            "Test sound systems, microphones, and backup power generator",
            "Set up recycling stations and post-event cleanup crew",
        ],
    },
}


def generate_demo_plan(request: EventRequest) -> EventPlanResponse:
    """
    Generates a realistic, deterministic, fully validated event plan when no Gemini API key is configured.
    Marked clearly with source='demo' and includes a demo mode warning.
    """
    theme_data = DEMO_THEMES.get(request.event_type, DEMO_THEMES["Community Event"])

    # Incorporate user custom theme if provided
    theme_name = request.theme if request.theme else theme_data["name"]
    theme_description = (
        f"Custom theme '{request.theme}' styled for {request.event_type} in {request.location}."
        if request.theme
        else theme_data["description"]
    )
    theme_info = ThemeInfo(
        name=theme_name,
        description=theme_description,
        color_palette=theme_data["color_palette"],
    )

    overview = (
        f"A meticulously organized plan for '{request.event_name}', a {request.event_type} "
        f"in {request.location} for {request.guest_count:,} guests with an estimated total budget "
        f"of {request.currency} {request.total_budget:,}."
    )
    if request.additional_preferences:
        overview += f" Tailored specifically with preferences: {request.additional_preferences}."

    # Raw budget items for reconciliation
    raw_budget_items = [
        RawAIBudgetItem(category="Venue", estimated_amount=int(request.total_budget * 0.30), notes="Primary venue rental, security deposit, and utilities"),
        RawAIBudgetItem(category="Catering", estimated_amount=int(request.total_budget * 0.30), notes=f"Food, beverages, and service staff for {request.guest_count} guests"),
        RawAIBudgetItem(category="Decoration", estimated_amount=int(request.total_budget * 0.15), notes=f"Floral, lighting, signage, and props aligned with '{theme_name}'"),
        RawAIBudgetItem(category="Entertainment", estimated_amount=int(request.total_budget * 0.08), notes="Sound equipment, artists, music, and interactive sessions"),
        RawAIBudgetItem(category="Photography", estimated_amount=int(request.total_budget * 0.07), notes="Lead photographer and video highlight reel"),
        RawAIBudgetItem(category="Miscellaneous", estimated_amount=int(request.total_budget * 0.03), notes="Stationery, printing, favors, and transit expenses"),
        RawAIBudgetItem(category="Contingency Reserve", estimated_amount=int(request.total_budget * 0.07), notes="Buffer for unexpected price variations or emergency requirements"),
    ]

    budget_breakdown = reconcile_budget(
        total_budget=request.total_budget,
        raw_items=raw_budget_items,
        event_type=request.event_type,
        currency=request.currency
    )

    timeline_items, timeline_warnings = process_timeline(
        event_date=request.event_date,
        raw_timeline=None,  # triggers intelligent defaults based on event type
        event_type=request.event_type
    )

    top_level_warnings = [
        "Demo mode: generated without an AI model"
    ]
    top_level_warnings.extend(timeline_warnings)

    return EventPlanResponse(
        id=str(uuid4()),
        source="demo",
        model=None,
        generated_at=datetime.now(timezone.utc),
        event_details=request,
        overview=overview,
        recommended_theme=theme_info,
        budget=budget_breakdown,
        checklist=theme_data["checklist"],
        timeline=timeline_items,
        decoration_suggestions=theme_data["decorations"],
        catering_suggestions=theme_data["catering"],
        entertainment_suggestions=theme_data["entertainment"],
        vendor_requirements=theme_data["vendors"],
        risks=theme_data["risks"],
        warnings=top_level_warnings,
    )
