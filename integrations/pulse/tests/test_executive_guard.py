"""Tests for the executive session guard.

Explicitly tests event titles that both do and don't contain the
executive-session keywords, as required by the Phase 7 spec.
"""

import pytest

from integrations.pulse.core.executive_guard import is_executive_session, sanitize_event

KEYWORDS = ["executive session", "exec session", "board executive"]


# ── is_executive_session ───────────────────────────────────────────

class TestIsExecutiveSession:
    """Substring matching against executive-session keywords."""

    @pytest.mark.parametrize(
        "title",
        [
            "Executive Session - Board Review",
            "Q1 exec session with counsel",
            "Board Executive planning",
            "executive session",
            "EXECUTIVE SESSION",  # case insensitive
            "Pre-meeting executive session notes",
            "Annual board executive retreat",
        ],
    )
    def test_matches_executive_keywords(self, title: str) -> None:
        assert is_executive_session(title, KEYWORDS) is True

    @pytest.mark.parametrize(
        "title",
        [
            "Staff meeting",
            "Grievance committee check-in",
            "Budget review",
            "Board meeting — public session",
            "Executive committee (non-session)",
            "Session planning",
            "",
        ],
    )
    def test_does_not_match_non_executive_titles(self, title: str) -> None:
        assert is_executive_session(title, KEYWORDS) is False


# ── sanitize_event ─────────────────────────────────────────────────

class TestSanitizeEvent:
    """Sanitization rules for executive-session events."""

    def _make_event(self, title: str = "Staff meeting") -> dict:
        return {
            "title": title,
            "time": "14:00",
            "duration_minutes": 90,
            "location": "Board Room",
            "attendees_count": 5,
            "body": "Discuss legal counsel report",
        }

    def test_non_executive_event_passes_through(self) -> None:
        event = self._make_event("Staff meeting")
        result = sanitize_event(event, KEYWORDS)

        assert result["title"] == "Staff meeting"
        assert result["location"] == "Board Room"
        assert result["attendees_count"] == 5
        assert result["body"] == "Discuss legal counsel report"
        assert result["duration_minutes"] == 90
        assert result["is_executive_session"] is False

    def test_executive_event_title_replaced(self) -> None:
        event = self._make_event("Executive Session - Board Review")
        result = sanitize_event(event, KEYWORDS)
        assert result["title"] == "Executive Session"

    def test_executive_event_body_omitted(self) -> None:
        event = self._make_event("Executive Session - Board Review")
        result = sanitize_event(event, KEYWORDS)
        assert result["body"] is None

    def test_executive_event_attendees_omitted(self) -> None:
        event = self._make_event("Exec Session with counsel")
        result = sanitize_event(event, KEYWORDS)
        assert result["attendees"] is None
        assert result["attendees_count"] == 0

    def test_executive_event_location_omitted(self) -> None:
        event = self._make_event("Board Executive retreat")
        result = sanitize_event(event, KEYWORDS)
        assert result["location"] is None

    def test_executive_event_duration_kept(self) -> None:
        event = self._make_event("Executive Session")
        result = sanitize_event(event, KEYWORDS)
        assert result["duration_minutes"] == 90

    def test_executive_event_flag_set(self) -> None:
        event = self._make_event("Exec Session")
        result = sanitize_event(event, KEYWORDS)
        assert result["is_executive_session"] is True

    def test_original_event_not_mutated(self) -> None:
        event = self._make_event("Executive Session")
        original_title = event["title"]
        sanitize_event(event, KEYWORDS)
        assert event["title"] == original_title

    def test_case_insensitive_match(self) -> None:
        event = self._make_event("EXECUTIVE SESSION - CLOSED")
        result = sanitize_event(event, KEYWORDS)
        assert result["is_executive_session"] is True
        assert result["title"] == "Executive Session"

    def test_partial_keyword_in_longer_title(self) -> None:
        event = self._make_event("Pre-meeting executive session notes for Feb")
        result = sanitize_event(event, KEYWORDS)
        assert result["is_executive_session"] is True
        assert result["title"] == "Executive Session"
        assert result["location"] is None
