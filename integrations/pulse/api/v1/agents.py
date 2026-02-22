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

from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import (
    AgentContextResponse,
    BoardContext,
    CalendarContext,
    CalendarEvent,
    CaptureRequest,
    CaptureResponse,
    CheckinRequest,
    CheckinResponse,
    CheckinStatusResponse,
    CheckinSlotStatus,
    EmailContext,
    GrievanceContext,
    GrievanceDeadlineItem,
    NextMeetingContext,
    SuggestedAction,
    TaskContext,
    TaskItem,
)
from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.business_days import days_until
from integrations.pulse.core.cache import (
    build_cache_key,
    get_cached,
    set_cached,
    invalidate,
)
from integrations.pulse.core.executive_guard import sanitize_event
from integrations.pulse.core.store import checkin_store
from integrations.pulse.db.models.board import BoardMeeting, BylawComplianceItem
from integrations.pulse.db.models.grievance import Grievance
from integrations.pulse.db.session import get_db

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

_CONTEXT_TTL = 300   # 5 minutes

# ---------------------------------------------------------------------------
# President context helpers — grievance + board context injection
# ---------------------------------------------------------------------------

_ALERT_WINDOW_DAYS = 7
PRESIDENT_AGENT_ID = "dave-president"


def _claim_values(user: dict[str, Any], claim_name: str) -> set[str]:
    """Normalize claim values that may be either a string or a list."""
    raw = user.get(claim_name)
    if isinstance(raw, str):
        return {raw.lower()}
    if isinstance(raw, list):
        return {str(v).lower() for v in raw}
    return set()


def _is_president_user(user: dict[str, Any]) -> bool:
    """Return True when the authenticated principal is the President role."""
    if user.get("user_id") == PRESIDENT_AGENT_ID:
        return True
    return "president" in _claim_values(user, "roles")


def _is_scheduler_service(user: dict[str, Any]) -> bool:
    """Return True when JWT claims identify the scheduler service principal."""
    roles = _claim_values(user, "roles")
    scopes = {
        scope.lower()
        for scope in str(user.get("scp", "")).split()
        if scope
    }
    return bool(roles.intersection({"scheduler", "service"}) or "scheduler.write" in scopes)


def _build_grievance_context(db: Session) -> GrievanceContext:
    """Build the grievances section of the context bundle from live DB data."""
    open_grievances: list[Grievance] = (
        db.query(Grievance)
        .filter(Grievance.status.in_(["open", "pending_arbitration"]))
        .all()
    )
    today = date.today()
    approaching: list[GrievanceDeadlineItem] = []

    for g in open_grievances:
        for dtype, ddate in [
            ("step1", g.step1_deadline),
            ("step2", g.step2_deadline),
            ("arbitration", g.arbitration_deadline),
        ]:
            remaining = days_until(ddate, today)
            if 0 <= remaining <= _ALERT_WINDOW_DAYS:
                approaching.append(
                    GrievanceDeadlineItem(
                        case_number=g.case_number,
                        facility=g.facility,
                        deadline_type=dtype,
                        days_remaining=remaining,
                        status=g.status,
                    )
                )

    approaching.sort(key=lambda a: a.days_remaining)
    return GrievanceContext(
        open_count=len(open_grievances),
        approaching_deadline=approaching,
    )


def _build_board_context(db: Session) -> BoardContext:
    """Build the board section of the context bundle from live DB data."""
    today = date.today()

    next_meeting: Optional[BoardMeeting] = (
        db.query(BoardMeeting)
        .filter(BoardMeeting.date >= today)
        .order_by(BoardMeeting.date.asc())
        .first()
    )

    due_30d = today + timedelta(days=30)
    compliance_count: int = (
        db.query(BylawComplianceItem)
        .filter(
            BylawComplianceItem.next_due <= due_30d,
            BylawComplianceItem.status != "completed",
        )
        .count()
    )

    next_ctx: Optional[NextMeetingContext] = None
    if next_meeting:
        days_away = (next_meeting.date - today).days
        next_ctx = NextMeetingContext(
            date=next_meeting.date.isoformat(),
            type=next_meeting.type,
            days_away=days_away,
        )

    return BoardContext(
        next_meeting=next_ctx,
        compliance_items_due_30d=compliance_count,
    )


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
    db: Session = Depends(get_db),
) -> AgentContextResponse:
    """Return the daily context bundle for the authenticated user's agent.

    Cached in Redis for 5 minutes per user.  Pass ``?cache_bust=true`` to
    force a fresh fetch (used by the agent heartbeat to get current state).

    Calendar events that match executive-session keywords are sanitised
    automatically by the executive-session guard.

    For the President agent, the response also includes:
    - grievances: open count and approaching deadlines (within 7 days)
    - board: next meeting and compliance items due within 30 days
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

    grievance_ctx = None
    board_ctx = None
    if _is_president_user(user):
        grievance_ctx = _build_grievance_context(db)
        board_ctx = _build_board_context(db)

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
        grievances=grievance_ctx,
        board=board_ctx,
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
    if body.agent_id != owner_id:
        if _is_scheduler_service(user):
            owner_id = body.agent_id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot submit check-ins for another agent",
            )

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
    """Quick-capture: Pulse sends raw note to agent for processing."""
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
