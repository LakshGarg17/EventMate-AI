from datetime import date, timedelta
from typing import List, Optional, Tuple

try:
    from app.schemas import RawAITimelineItem, TimelineItem
except ImportError:
    from backend.app.schemas import RawAITimelineItem, TimelineItem


PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

DEFAULT_TASKS_BY_EVENT = {
    "Wedding": [
        ("Finalize Venue & Date", "Confirm venue contract and pay deposit", "High", "Venue", 60),
        ("Book Key Vendors", "Hire caterer, photographer, and decorator", "High", "Vendors", 45),
        ("Send Invitations", "Distribute invitations and collect RSVPs", "Medium", "Guest Management", 30),
        ("Menu Tasting & Theme Finalization", "Sample catering menu and finalize color palette", "Medium", "Catering & Decor", 20),
        ("Sound & Entertainment Briefing", "Share playlist and itinerary with DJ/band", "Low", "Entertainment", 10),
        ("Final Vendor Walkthrough", "Confirm arrival times and setup logistics with all vendors", "High", "Logistics", 2),
        ("Day-of Event Coordination", "Coordinate arrivals and oversee celebration execution", "High", "Day of Event", 0),
    ],
    "Birthday": [
        ("Select Venue & Theme", "Lock in the party venue or home arrangement and theme", "High", "Venue", 21),
        ("Send Out Invites", "Send digital or printed invitations to guests", "Medium", "Guest Management", 14),
        ("Order Cake & Catering", "Confirm customized cake and food/beverage menu", "High", "Catering", 10),
        ("Source Decorations & Supplies", "Acquire balloons, banners, tableware, and lighting", "Medium", "Decoration", 7),
        ("Plan Games & Playlist", "Curate activities, music playlist, and party favors", "Low", "Entertainment", 3),
        ("Setup & Final Preparation", "Decorate space and greet early arrivals", "High", "Day of Event", 0),
    ],
    "Community Event": [
        ("Venue & Permit Approvals", "Secure municipal permits and community space reservation", "High", "Permits & Venue", 30),
        ("Announce Event & Marketing", "Publish announcements on community channels and local boards", "Medium", "Promotion", 20),
        ("Arrange Equipment & Seating", "Book AV sound systems, chairs, stage, and tables", "High", "Logistics", 14),
        ("Volunteer & Staff Briefing", "Assign roles for registration, hospitality, and crowd control", "Medium", "Coordination", 5),
        ("Final Safety & Sanitation Check", "Verify emergency exits, first aid kits, and trash receptacles", "High", "Safety", 1),
        ("Event Day Execution", "Open registration, coordinate speakers/activities, and oversee cleanup", "High", "Day of Event", 0),
    ],
}


def process_timeline(
    event_date: date,
    raw_timeline: Optional[List[RawAITimelineItem]],
    event_type: str,
    today: Optional[date] = None,
) -> Tuple[List[TimelineItem], List[str]]:
    """
    Validates, chronologically sorts, and computes deterministic due dates for timeline tasks.
    Returns (timeline_items, timeline_warnings).
    """
    if today is None:
        today = date.today()

    warnings: List[str] = []
    days_until_event = (event_date - today).days

    if days_until_event < 0:
        warnings.append(f"Event date ({event_date.isoformat()}) is in the past relative to today ({today.isoformat()}).")
    elif days_until_event == 0:
        warnings.append("Event is scheduled for today! Immediate same-day coordination required.")
    elif days_until_event < 7:
        warnings.append(f"Short preparation window: Event is only {days_until_event} days away. High-priority tasks must be expedited immediately.")

    items_to_process: List[RawAITimelineItem] = []

    if raw_timeline and len(raw_timeline) > 0:
        items_to_process = raw_timeline
    else:
        # Fall back to default tasks for the event type
        defaults = DEFAULT_TASKS_BY_EVENT.get(event_type, DEFAULT_TASKS_BY_EVENT["Community Event"])
        for task, desc, prio, cat, days in defaults:
            items_to_process.append(
                RawAITimelineItem(
                    task=task,
                    description=desc,
                    priority=prio if prio in ("High", "Medium", "Low") else "Medium",
                    category=cat,
                    days_before=days
                )
            )

    processed_items: List[TimelineItem] = []

    for item in items_to_process:
        task_name = (item.task or "").strip()
        if not task_name:
            continue

        desc = (item.description or "").strip()
        prio = item.priority if item.priority in ("High", "Medium", "Low") else "Medium"
        cat = (item.category or "General").strip()

        # Clamp days_before: must be non-negative (tasks cannot be after event date)
        days_before = item.days_before
        task_warning: Optional[str] = None
        if days_before < 0:
            days_before = 0
            task_warning = "Task was scheduled after event date; adjusted to event day."

        computed_due = event_date - timedelta(days=days_before)
        is_overdue = False
        is_unrealistic = False

        if computed_due < today:
            is_overdue = True
            is_unrealistic = True
            overdue_days = (today - computed_due).days
            task_warning = f"Recommended date was {overdue_days} days ago. Compressed to today as an urgent action."
            final_due = today
        elif computed_due > event_date:
            final_due = event_date
            is_unrealistic = True
            task_warning = "Task date adjusted to not exceed event date."
        else:
            final_due = computed_due

        processed_items.append(
            TimelineItem(
                task=task_name,
                description=desc,
                priority=prio,
                category=cat,
                due_date=final_due,
                days_before=days_before,
                is_overdue=is_overdue,
                is_unrealistic=is_unrealistic,
                warning=task_warning
            )
        )

    # Sort chronologically: due_date ascending, then priority
    processed_items.sort(key=lambda t: (t.due_date, PRIORITY_ORDER.get(t.priority, 1)))

    # Flag top-level warning if any tasks are overdue
    overdue_count = sum(1 for t in processed_items if t.is_overdue)
    if overdue_count > 0:
        warnings.append(f"{overdue_count} preparation task(s) are overdue and require immediate execution.")

    return processed_items, warnings
