from datetime import date, datetime, timezone
from typing import Optional

_frozen_today: Optional[date] = None
_frozen_now: Optional[datetime] = None


def get_today() -> date:
    """Returns today's date, or a frozen date if overridden for testing."""
    global _frozen_today
    if _frozen_today is not None:
        return _frozen_today
    return date.today()


def set_frozen_today(d: Optional[date]) -> None:
    """Sets or clears a frozen date for reproducible testing."""
    global _frozen_today
    _frozen_today = d


def get_now() -> datetime:
    """Returns the current UTC datetime, or a frozen datetime if overridden for testing."""
    global _frozen_now
    if _frozen_now is not None:
        return _frozen_now
    return datetime.now(timezone.utc)


def set_frozen_now(dt: Optional[datetime]) -> None:
    """Sets or clears a frozen datetime for reproducible testing."""
    global _frozen_now
    _frozen_now = dt
