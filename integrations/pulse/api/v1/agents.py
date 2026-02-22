"""Agent-plane API endpoints for Pulse.

All endpoints live under ``/api/v1/agents/`` and require Azure AD JWT
authentication.  They are additive — no existing Pulse endpoints are
modified.

Caching
-------
GET /context is cached in Redis for 5 minutes per user.
Pass ``?cache_bust=true`` to force a fresh fetch.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

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
    SuggestedAction,
    TaskContext,
    TaskItem,
)
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.cache import (
    build_cache_key,
    get_cached,
    set_cached,
    invalidate,
)
from integrations.pulse.core.executive_guard import sanitize_event
from integrations.pulse.core.store import checkin_store

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

_CONTEXT_TTL = 300   # 5 minutes


# ---------------------------------------------------------------------------
# Stub data providers — replace with real Pulse DB / MS Graph queries.
# ---------------------------------------------------------------------------

def _stub_calendar_events() -> list[dict[str, Any]]:
    """Return placeholder calendar events for development."""
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
    cache_bust: bool = Query(False, alias="cache_bust"),
    user: dict[str, Any] = Depends(get_current_user),
) -> AgentContextResponse:
    """Return the daily context bundle for the authenticated user's agent.

    Cached in Redis for 5 minutes per user.  Pass ``?cache_bust=true`` to
    force a fresh fetch (used by the agent heartbeat to get current state).

    Calendar events that match executive-session keywords are sanitised
    automatically by the executive-session guard.
    """
    owner_id: str = user["user_id"]
    cache_key = build_cache_key("agent_context", owner_id)

    if not cache_bust:
        cached = await get_cached(cache_key)
        if cached is not None:
            return AgentContextResponse(**cached)

    # Fetch raw events then sanitize
    today_events = [CalendarEvent(**sanitize_event(e)) for e in _stub_calendar_events()]
    upcoming_events = [CalendarEvent(**sanitize_event(e)) for e in _stub_upcoming_events()]
    task_data = _stub_tasks()
    email_data = _stub_email()

    response = AgentContextResponse(
        owner_id=owner_id,
        generated_at=datetime.utcnow().isoformat() + "Z",
        calendar=CalendarContext(today=today_events, upcoming_48h=upcoming_events),
        tasks=TaskContext(
            overdue=task_data["overdue"],
            due_today=task_data["due_today"],
            high_priority=task_data["high_priority"],
            items=[TaskItem(**t) for t in task_data["items"]],
        ),
        email=EmailContext(**email_data),
    )

    await set_cached(cache_key, response.model_dump(), _CONTEXT_TTL)
    return response


# ---------------------------------------------------------------------------
# POST /api/v1/agents/checkin
# ---------------------------------------------------------------------------

@router.post("/checkin", response_model=CheckinResponse)
async def post_agent_checkin(
    body: CheckinRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckinResponse:
    """Accept a morning or evening check-in from an agent.

    Invalidates the context cache so the next fetch reflects the new state.
    """
    owner_id: str = user["user_id"]
    checkin_id = checkin_store.save(owner_id, body.model_dump())
    # Invalidate context cache so next fetch picks up updated state
    await invalidate(f"agent_context:{owner_id}")
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
