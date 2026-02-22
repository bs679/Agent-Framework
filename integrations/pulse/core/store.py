"""Lightweight in-memory store for agent check-ins.

In production this would be backed by the Pulse database.  For now we
keep today's check-ins in memory, which is sufficient for the API
contract and sidebar display.

TTL / stale-entry cleanup
--------------------------
Entries older than RETENTION_DAYS are pruned on each write to prevent
the store growing unboundedly across day boundaries during long-running
processes.  The default retention is 2 days (today + yesterday) so that
dashboards loaded just after midnight can still show yesterday's summary.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

RETENTION_DAYS: int = 2


class CheckinStore:
    """Thread-safe (single-process) store for daily agent check-ins."""

    def __init__(self, retention_days: int = RETENTION_DAYS) -> None:
        # key: (owner_id, date_str) → list of checkin dicts
        self._checkins: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._retention_days = retention_days

    def _purge_stale(self) -> None:
        """Remove entries older than retention_days. Called on every write."""
        cutoff = (date.today() - timedelta(days=self._retention_days)).isoformat()
        stale = [key for key in self._checkins if key[1] < cutoff]
        for key in stale:
            del self._checkins[key]

    def save(self, owner_id: str, checkin: dict[str, Any]) -> str:
        """Persist a check-in and return a generated checkin_id."""
        self._purge_stale()
        checkin_id = uuid.uuid4().hex[:12]
        today = date.today().isoformat()
        key = (owner_id, today)
        entry = {**checkin, "checkin_id": checkin_id, "stored_at": datetime.utcnow().isoformat()}
        self._checkins.setdefault(key, []).append(entry)
        return checkin_id

    def get_today(self, owner_id: str) -> list[dict[str, Any]]:
        """Return all check-ins stored for *owner_id* today."""
        today = date.today().isoformat()
        return list(self._checkins.get((owner_id, today), []))

    def get_today_status(self, owner_id: str) -> dict[str, Any]:
        """Return morning/evening status summary for the Pulse sidebar."""
        checkins = self.get_today(owner_id)

        morning_done = False
        morning_time: str | None = None
        evening_done = False
        evening_time: str | None = None

        for c in checkins:
            ctype = c.get("checkin_type")
            ts = c.get("timestamp", "")
            # Extract HH:MM from ISO timestamp
            try:
                parsed = datetime.fromisoformat(ts)
                hhmm = parsed.strftime("%H:%M")
            except (ValueError, TypeError):
                hhmm = None

            if ctype == "morning":
                morning_done = True
                morning_time = hhmm
            elif ctype == "evening":
                evening_done = True
                evening_time = hhmm

        return {
            "morning": {
                "completed": morning_done,
                "time": morning_time,
            },
            "evening": {
                "completed": evening_done,
                "time": evening_time,
                "scheduled_for": "17:00",
            },
        }

    def get_latest_alerts(self, owner_id: str) -> list[dict[str, Any]]:
        """Return all alerts from today's check-ins (for the alert banner)."""
        alerts: list[dict[str, Any]] = []
        for c in self.get_today(owner_id):
            alerts.extend(c.get("alerts", []))
        return alerts


# Module-level singleton — imported by the router.
checkin_store = CheckinStore()
