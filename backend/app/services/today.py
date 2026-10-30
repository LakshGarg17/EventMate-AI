from datetime import date
from typing import Optional

_frozen_today: Optional[date] = None


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
