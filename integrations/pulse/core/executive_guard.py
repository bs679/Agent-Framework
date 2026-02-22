"""Executive Session Guard — sanitises calendar events that match
executive-session keywords before they reach the agent context API.

Keywords are sourced from the EXECUTIVE_SESSION_KEYWORDS env var
(comma-separated, case-insensitive substring match against event title).

Sanitisation rules when is_executive_session is True:
  - title  → "Executive Session"
  - body   → omitted (set to None)
  - attendees → omitted (set to None / empty)
  - location  → omitted (set to None)
  - duration  → kept as-is
  - is_executive_session → True
"""

from __future__ import annotations

from typing import Any

from integrations.pulse.core.config import get_settings


def is_executive_session(title: str, keywords: list[str] | None = None) -> bool:
    """Return True if *title* contains any executive-session keyword.

    Parameters
    ----------
    title:
        The calendar event title to check.
    keywords:
        Optional explicit keyword list.  Falls back to settings.
    """
    if keywords is None:
        keywords = get_settings().executive_keywords_list
    title_lower = title.lower()
    return any(kw in title_lower for kw in keywords)


def sanitize_event(
    event: dict[str, Any],
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Return a sanitised copy of *event* if it is an executive session.

    The input dict is never mutated — a new dict is returned.

    Expected input keys (at minimum):
        title, time, duration_minutes, location, attendees_count

    Extra keys are passed through unchanged unless the event is flagged.
    """
    if keywords is None:
        keywords = get_settings().executive_keywords_list

    title = event.get("title", "")
    flagged = is_executive_session(title, keywords)

    result = dict(event)  # shallow copy
    result["is_executive_session"] = flagged

    if flagged:
        result["title"] = "Executive Session"
        result["body"] = None
        result["attendees"] = None
        result["attendees_count"] = 0
        result["location"] = None

    return result
