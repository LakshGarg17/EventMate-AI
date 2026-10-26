from datetime import date, timedelta
from app.schemas import RawAITimelineItem
from app.services.timeline import process_timeline


def test_timeline_due_date_calculation_and_sorting():
    today = date(2026, 10, 25)
    event_date = date(2026, 12, 25)  # 61 days away

    raw_items = [
        RawAITimelineItem(task="Day of event setup", description="On-site setup", priority="High", category="Setup", days_before=0),
        RawAITimelineItem(task="Book venue", description="Sign contract", priority="High", category="Venue", days_before=50),
        RawAITimelineItem(task="Send invites", description="RSVP collection", priority="Medium", category="Guests", days_before=30),
    ]

    items, warnings = process_timeline(
        event_date=event_date,
        raw_timeline=raw_items,
        event_type="Wedding",
        today=today
    )

    # Chronologically sorted by due_date ascending
    assert len(items) == 3
    assert items[0].task == "Book venue"
    assert items[0].due_date == date(2026, 11, 5)
    assert items[1].task == "Send invites"
    assert items[1].due_date == date(2026, 11, 25)
    assert items[2].task == "Day of event setup"
    assert items[2].due_date == date(2026, 12, 25)
    assert not any(item.is_overdue for item in items)


def test_overdue_and_unrealistic_dates_are_flagged_and_compressed():
    today = date(2026, 10, 25)
    event_date = date(2026, 10, 30)  # 5 days away

    raw_items = [
        # Recommended 30 days before event -> Oct 30 - 30 days = Sept 30 (which is in the past!)
        RawAITimelineItem(task="Book primary venue", description="Overdue booking", priority="High", category="Venue", days_before=30),
        RawAITimelineItem(task="Pick up cake", description="Day before", priority="Medium", category="Catering", days_before=1),
    ]

    items, warnings = process_timeline(
        event_date=event_date,
        raw_timeline=raw_items,
        event_type="Birthday",
        today=today
    )

    overdue_task = items[0]
    assert overdue_task.task == "Book primary venue"
    assert overdue_task.is_overdue is True
    assert overdue_task.is_unrealistic is True
    assert overdue_task.due_date == today  # compressed to today
    assert overdue_task.warning is not None
    assert "Recommended date was" in overdue_task.warning

    # Check top-level warnings include overdue count and short prep window
    assert any("overdue" in w.lower() for w in warnings)
    assert any("short preparation window" in w.lower() for w in warnings)


def test_event_tomorrow_produces_warning():
    today = date(2026, 10, 25)
    event_date = date(2026, 10, 26)  # tomorrow!

    items, warnings = process_timeline(
        event_date=event_date,
        raw_timeline=None,
        event_type="Community Event",
        today=today
    )

    assert any("Short preparation window" in w for w in warnings)


def test_task_after_event_date_is_clamped():
    today = date(2026, 10, 25)
    event_date = date(2026, 11, 25)

    raw_items = [
        RawAITimelineItem(task="After Party Clean", description="Post event", priority="Low", category="Cleaning", days_before=-2)
    ]

    items, warnings = process_timeline(
        event_date=event_date,
        raw_timeline=raw_items,
        event_type="Birthday",
        today=today
    )

    assert items[0].due_date <= event_date
    assert items[0].warning is not None
