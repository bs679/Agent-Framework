"""Business-day arithmetic for grievance deadline calculation.

CT state holidays are observed by CHCA-represented hospitals. The
``holidays`` library covers all US federal holidays; state-specific
additions (CT Columbus Day replacement, etc.) can be added to the
``_CT_EXTRA_HOLIDAYS`` set if needed.

Usage:
    deadline = add_business_days(filed_date, 10)   # Step 1: +10 bd
    deadline = add_business_days(step1_date, 15)   # Step 2: +15 bd
    deadline = add_business_days(step2_date, 30)   # Arbitration: +30 bd (default)
"""

from __future__ import annotations

from datetime import date, timedelta

try:
    import holidays as _holidays_lib  # type: ignore[import]

    def _is_us_holiday(d: date) -> bool:
        us = _holidays_lib.country_holidays("US", years=d.year)
        return d in us

except ImportError:
    # Fallback if the ``holidays`` package is not installed — only skips weekends.
    def _is_us_holiday(d: date) -> bool:  # type: ignore[misc]
        return False


def is_business_day(d: date) -> bool:
    """Return True if *d* is a Monday-Friday non-holiday."""
    return d.weekday() < 5 and not _is_us_holiday(d)


def add_business_days(start: date, days: int) -> date:
    """Return the date *days* business days after *start* (exclusive of *start*).

    Args:
        start: The reference date (filing date, step deadline, etc.)
        days:  Number of business days to advance. Must be positive.

    Returns:
        The resulting business day.

    Raises:
        ValueError: If *days* is not positive.
    """
    if days <= 0:
        raise ValueError(f"days must be positive, got {days}")

    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_business_day(current):
            remaining -= 1
    return current


def days_until(target: date, today: date | None = None) -> int:
    """Return how many calendar days remain until *target* from *today*.

    Negative means the deadline has already passed.
    """
    ref = today or date.today()
    return (target - ref).days
