"""Agent-plane API endpoints for Pulse.

All endpoints live under ``/api/v1/agents/`` and require Azure AD JWT
authentication.  They are additive — no existing Pulse endpoints are
modified.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from integrations.pulse.api.v1.schemas import (
    AgentContextResponse,
    CalendarContext,
    CalendarEvent,
    CaptureRequest,
    CaptureResponse,
    CheckinRequest,
    CheckinResponse,
    CheckinStatusResponse,
    CheckinSlotStatus,
    EmailContext,
    FinanceContext,
    SchedulingContext,
    SuggestedAction,
    TaskContext,
    TaskItem,
)
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.executive_guard import sanitize_event
from integrations.pulse.core.roles import _has_officer_role
from integrations.pulse.core.store import checkin_store
from integrations.pulse.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Stub data providers — replace with real Pulse DB / MS Graph queries.
# ---------------------------------------------------------------------------

def _stub_calendar_events() -> list[dict[str, Any]]:
    """Return placeholder calendar events for development."""
    now = datetime.utcnow()
    return [
        {
            "title": "Staff meeting",
            "time": "09:00",
            "duration_minutes": 60,
            "location": "Room 201",
            "attendees_count": 8,
        },
        {
            "title": "Executive Session - Board Review",
            "time": "14:00",
            "duration_minutes": 90,
            "location": "Board Room",
            "attendees_count": 5,
        },
        {
            "title": "Grievance committee check-in",
            "time": "16:00",
            "duration_minutes": 30,
            "location": "Zoom",
            "attendees_count": 4,
        },
    ]


def _stub_upcoming_events() -> list[dict[str, Any]]:
    """Placeholder upcoming events (next 48 h)."""
    return [
        {
            "title": "Budget review",
            "time": "10:00",
            "duration_minutes": 120,
            "location": "Finance Office",
            "attendees_count": 3,
        },
    ]


def _stub_tasks() -> dict[str, Any]:
    return {
        "overdue": 1,
        "due_today": 3,
        "high_priority": 2,
        "items": [
            {"id": "t-001", "title": "File Waterbury grievance #24-117", "due_date": "2026-02-22", "priority": "high"},
            {"id": "t-002", "title": "Review steward reports", "due_date": "2026-02-21", "priority": "medium"},
            {"id": "t-003", "title": "Prepare bargaining notes", "due_date": "2026-02-21", "priority": "high"},
        ],
    }


def _stub_email() -> dict[str, Any]:
    return {"unread_count": 12, "urgent_count": 2}


# ---------------------------------------------------------------------------
# GET /api/v1/agents/context
# ---------------------------------------------------------------------------

@router.get("/context", response_model=AgentContextResponse)
async def get_agent_context(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentContextResponse:
    """Return the daily context bundle for the authenticated user's agent.

    Calendar events that match executive-session keywords are sanitised
    automatically by the executive-session guard.

    For OFFICER role users, the response also includes role-specific context:
      - SecTreas: 'finance' section with pending co-signatures and dues arrears
      - ExecSec:  'scheduling' section with minutes drafts and pending requests
    """
    owner_id: str = user["user_id"]

    # Fetch raw events then sanitize each through the guard
    today_raw = _stub_calendar_events()
    upcoming_raw = _stub_upcoming_events()

    today_events = [
        CalendarEvent(**sanitize_event(evt)) for evt in today_raw
    ]
    upcoming_events = [
        CalendarEvent(**sanitize_event(evt)) for evt in upcoming_raw
    ]

    task_data = _stub_tasks()
    email_data = _stub_email()

    # Build officer-specific context sections
    finance_ctx: FinanceContext | None = None
    scheduling_ctx: SchedulingContext | None = None

    if _has_officer_role(user):
        try:
            from integrations.pulse.api.v1.finance import build_finance_context
            finance_ctx = FinanceContext(**build_finance_context(db))
        except Exception:
            pass  # Non-blocking: officer context is best-effort

        try:
            from integrations.pulse.api.v1.minutes_api import build_scheduling_context
            scheduling_ctx = SchedulingContext(**build_scheduling_context(db))
        except Exception:
            pass

    return AgentContextResponse(
        owner_id=owner_id,
        generated_at=datetime.utcnow().isoformat() + "Z",
        calendar=CalendarContext(
            today=today_events,
            upcoming_48h=upcoming_events,
        ),
        tasks=TaskContext(
            overdue=task_data["overdue"],
            due_today=task_data["due_today"],
            high_priority=task_data["high_priority"],
            items=[TaskItem(**t) for t in task_data["items"]],
        ),
        email=EmailContext(**email_data),
        finance=finance_ctx,
        scheduling=scheduling_ctx,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/agents/checkin
# ---------------------------------------------------------------------------

@router.post("/checkin", response_model=CheckinResponse)
async def post_agent_checkin(
    body: CheckinRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckinResponse:
    """Accept a morning or evening check-in from an agent."""
    owner_id: str = user["user_id"]
    checkin_id = checkin_store.save(owner_id, body.model_dump())
    return CheckinResponse(status="accepted", checkin_id=checkin_id)


# ---------------------------------------------------------------------------
# GET /api/v1/agents/checkin/status
# ---------------------------------------------------------------------------

@router.get("/checkin/status", response_model=CheckinStatusResponse)
async def get_checkin_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckinStatusResponse:
    """Return today's morning/evening check-in status for the sidebar."""
    owner_id: str = user["user_id"]
    data = checkin_store.get_today_status(owner_id)
    return CheckinStatusResponse(
        morning=CheckinSlotStatus(**data["morning"]),
        evening=CheckinSlotStatus(**data["evening"]),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/agents/capture
# ---------------------------------------------------------------------------

@router.post("/capture", response_model=CaptureResponse)
async def post_capture(
    body: CaptureRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CaptureResponse:
    """Quick-capture: Pulse sends raw note to agent for processing.

    In production this forwards to the agent plane for NLP processing.
    For now returns a heuristic-based suggestion.
    """
    content_lower = body.content.lower()

    # Simple heuristic routing until agent plane NLP is wired up
    if any(kw in content_lower for kw in ("follow up", "remind", "deadline", "due")):
        action = SuggestedAction.create_task
        details = f"Create task: {body.content}"
    elif any(kw in content_lower for kw in ("reply", "respond", "email")):
        action = SuggestedAction.reply_email
        details = f"Draft reply regarding: {body.content}"
    elif any(kw in content_lower for kw in ("remember", "note", "save")):
        action = SuggestedAction.add_to_memory
        details = f"Saved to agent memory: {body.content}"
    else:
        action = SuggestedAction.flag_for_review
        details = f"Flagged for review: {body.content}"

    return CaptureResponse(suggested_action=action, details=details)
