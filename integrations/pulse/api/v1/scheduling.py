"""Scheduling coordination API — Executive Secretary officer capability.

Endpoints at /api/v1/scheduling/:

  GET  /availability       — find available time slots via MS Graph findMeetingTimes
  POST /meeting-request    — create draft calendar event via MS Graph (NOT confirmed)

MS Graph integration is stubbed with clearly marked placeholders.
When MSGRAPH_CLIENT_ID and MSGRAPH_CLIENT_SECRET are set, wire in the real
MS Graph findMeetingTimes and createEvent calls.

All endpoints require valid JWT.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from integrations.pulse.core.auth import get_current_user
from integrations.pulse.db.models.minutes import PulseTask
from integrations.pulse.db.session import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduling", tags=["scheduling"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MeetingRequestCreate(BaseModel):
    title: str
    participants: list[str]
    preferred_times: list[str]
    notes: Optional[str] = None


class TimeSlot(BaseModel):
    start: str
    end: str
    confidence: str = "medium"


class AvailabilityResponse(BaseModel):
    participants: list[str]
    duration_minutes: int
    window_days: int
    suggested_slots: list[TimeSlot]
    source: str = "ms_graph"


class MeetingRequestOut(BaseModel):
    request_id: int
    title: str
    participants: list[str]
    status: str
    message: str


# ---------------------------------------------------------------------------
# MS Graph helpers (stubbed — wire to real MS Graph when credentials available)
# ---------------------------------------------------------------------------

_MSGRAPH_AVAILABLE = bool(
    os.environ.get("MSGRAPH_CLIENT_ID") and os.environ.get("MSGRAPH_CLIENT_SECRET")
)


async def _find_meeting_times_stub(
    participant_emails: list[str],
    duration_minutes: int,
    window_days: int,
) -> list[TimeSlot]:
    """Stub for MS Graph findMeetingTimes.

    Replace with real MS Graph API call when credentials are available:
      POST https://graph.microsoft.com/v1.0/me/findMeetingTimes
    """
    logger.info(
        "MS Graph findMeetingTimes stub called for %d participants, "
        "%d min, %d day window",
        len(participant_emails),
        duration_minutes,
        window_days,
    )
    # Generate plausible stub slots starting tomorrow
    base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    base += timedelta(days=1)
    slots = []
    for i in range(3):
        slot_start = base + timedelta(days=i, hours=i)
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        slots.append(
            TimeSlot(
                start=slot_start.isoformat(),
                end=slot_end.isoformat(),
                confidence="high" if i == 0 else "medium",
            )
        )
    return slots


async def _create_draft_event_stub(
    title: str,
    participants: list[str],
    preferred_times: list[str],
) -> str:
    """Stub for MS Graph createEvent (draft, not confirmed).

    Replace with real MS Graph API call:
      POST https://graph.microsoft.com/v1.0/me/events
      body: {"isDraft": true, ...}
    """
    logger.info("MS Graph createEvent (draft) stub called: title=%s", title)
    return f"draft-event-stub-{hash(title) & 0xFFFF:04x}"


# ---------------------------------------------------------------------------
# GET /api/v1/scheduling/availability
# ---------------------------------------------------------------------------


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    participant_emails: list[str] = Query(..., alias="participant_emails[]"),
    duration_minutes: int = Query(60, ge=15, le=480),
    window_days: int = Query(14, ge=1, le=60),
    user: dict[str, Any] = Depends(get_current_user),
) -> AvailabilityResponse:
    """Find available meeting times for all participants.

    Calls MS Graph findMeetingTimes and returns ranked intersection of free slots.
    Currently returns stub data when MS Graph credentials are not configured.
    """
    if not participant_emails:
        raise HTTPException(status_code=422, detail="At least one participant email is required")

    if _MSGRAPH_AVAILABLE:
        # TODO: wire real MS Graph call here
        # access_token = await _get_msgraph_token()
        # slots = await _find_meeting_times_real(participant_emails, duration_minutes, window_days, access_token)
        raise HTTPException(
            status_code=501,
            detail="Real MS Graph integration not yet wired. Set MSGRAPH_CLIENT_ID and CLIENT_SECRET.",
        )

    slots = await _find_meeting_times_stub(participant_emails, duration_minutes, window_days)
    return AvailabilityResponse(
        participants=participant_emails,
        duration_minutes=duration_minutes,
        window_days=window_days,
        suggested_slots=slots,
        source="stub",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/scheduling/meeting-request
# ---------------------------------------------------------------------------


@router.post("/meeting-request", response_model=MeetingRequestOut, status_code=201)
async def create_meeting_request(
    body: MeetingRequestCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingRequestOut:
    """Create a draft calendar event and notify ExecSec for confirmation.

    The event is created as a DRAFT only — it is NOT confirmed or sent until
    ExecSec reviews and confirms.
    """
    if _MSGRAPH_AVAILABLE:
        # TODO: wire real MS Graph call here
        raise HTTPException(
            status_code=501,
            detail="Real MS Graph integration not yet wired.",
        )

    _draft_event_id = await _create_draft_event_stub(
        body.title, body.participants, body.preferred_times
    )

    # Create a task for ExecSec to review and confirm the meeting request
    task = PulseTask(
        title=f"Review meeting request: {body.title}",
        description=(
            f"Meeting request from {user['user_id']}:\n"
            f"Title: {body.title}\n"
            f"Participants: {', '.join(body.participants)}\n"
            f"Preferred times: {', '.join(body.preferred_times)}\n"
            f"Notes: {body.notes or 'None'}\n\n"
            "Draft calendar event created — please review and confirm."
        ),
        assigned_to="execsec",
        created_by=user["user_id"],
        status="open",
        related_object=f"draft_event:{_draft_event_id}",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(
        "Meeting request '%s' created by %s — draft event %s, task %d assigned to ExecSec",
        body.title,
        user["user_id"],
        _draft_event_id,
        task.id,
    )

    return MeetingRequestOut(
        request_id=task.id,
        title=body.title,
        participants=body.participants,
        status="draft_pending_confirmation",
        message="Draft event created. ExecSec has been notified for confirmation.",
    )
