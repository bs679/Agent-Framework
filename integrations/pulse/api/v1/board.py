"""Module 4 — Executive Board Support endpoints.

All endpoints require a valid Azure AD JWT.

Routes:
  GET  /api/v1/board/meetings      — List board meeting records
  POST /api/v1/board/meetings      — Create meeting record
  GET  /api/v1/board/compliance    — Bylaw compliance calendar
  GET  /api/v1/board/agenda-draft  — AI-generated meeting agenda draft (Kimi K2)

Security note:
  The agenda draft includes grievance counts by facility but NEVER includes
  grievance details, member names, or case specifics — those stay in the
  grievances module under proper access controls.
  Board meetings in executive_session are never auto-recorded or auto-shared.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from integrations.pulse.core.auth import get_current_user
from integrations.pulse.db.models.board import BoardMeeting, BylawComplianceItem
from integrations.pulse.db.models.grievance import Grievance
from integrations.pulse.db.session import get_db

router = APIRouter(prefix="/api/v1/board", tags=["board"])

VALID_MEETING_TYPES = {"regular", "special", "executive_session"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class BoardMeetingCreate(BaseModel):
    date: date
    location: Optional[str] = None
    type: str = "regular"
    quorum_met: Optional[bool] = None
    notes: Optional[str] = None


class BoardMeetingOut(BaseModel):
    id: int
    date: date
    location: Optional[str]
    type: str
    quorum_met: Optional[bool]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class BylawComplianceOut(BaseModel):
    id: int
    requirement: str
    frequency: str
    last_completed: Optional[date]
    next_due: date
    assigned_to: Optional[str]
    status: str
    days_until_due: int

    model_config = {"from_attributes": True}


class AgendaItem(BaseModel):
    section: str
    items: list[str]


class AgendaDraftResponse(BaseModel):
    meeting_date: Optional[date]
    generated_at: str
    draft: str
    model_used: str
    routed_to: str
    note: str = "Draft agenda for Dave's review. Never auto-distributed."


# ---------------------------------------------------------------------------
# GET /api/v1/board/meetings
# ---------------------------------------------------------------------------

@router.get("/meetings", response_model=list[BoardMeetingOut])
def list_meetings(
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BoardMeetingOut]:
    """List all board meeting records, most recent first."""
    meetings = db.query(BoardMeeting).order_by(BoardMeeting.date.desc()).all()
    return [BoardMeetingOut.model_validate(m) for m in meetings]


# ---------------------------------------------------------------------------
# POST /api/v1/board/meetings
# ---------------------------------------------------------------------------

@router.post("/meetings", response_model=BoardMeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(
    body: BoardMeetingCreate,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BoardMeetingOut:
    """Create a new board meeting record."""
    if body.type not in VALID_MEETING_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"type must be one of: {sorted(VALID_MEETING_TYPES)}",
        )

    meeting = BoardMeeting(
        date=body.date,
        location=body.location,
        type=body.type,
        quorum_met=body.quorum_met,
        notes=body.notes,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return BoardMeetingOut.model_validate(meeting)


# ---------------------------------------------------------------------------
# GET /api/v1/board/compliance
# ---------------------------------------------------------------------------

@router.get("/compliance", response_model=list[BylawComplianceOut])
def compliance_calendar(
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BylawComplianceOut]:
    """Return the bylaw compliance calendar, sorted by soonest due date."""
    today = date.today()
    items = (
        db.query(BylawComplianceItem)
        .order_by(BylawComplianceItem.next_due.asc())
        .all()
    )

    out = []
    for item in items:
        days_remaining = (item.next_due - today).days
        out.append(
            BylawComplianceOut(
                id=item.id,
                requirement=item.requirement,
                frequency=item.frequency,
                last_completed=item.last_completed,
                next_due=item.next_due,
                assigned_to=item.assigned_to,
                status=item.status,
                days_until_due=days_remaining,
            )
        )
    return out


# ---------------------------------------------------------------------------
# GET /api/v1/board/agenda-draft
# ---------------------------------------------------------------------------

@router.get("/agenda-draft", response_model=AgendaDraftResponse)
async def agenda_draft(
    request: Request,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgendaDraftResponse:
    """Generate a draft board meeting agenda for Dave's review.

    Pulls together:
    - Approaching bylaw compliance items (due within 60 days)
    - Open grievance counts by facility (counts only — no member details)
    - Next scheduled meeting date

    Routes to Kimi K2 (non-sensitive content, quality matters).
    Falls back to Ollama. Never auto-sends or distributes the draft.
    """
    today = date.today()
    ai_router = request.app.state.ai_router

    # --- Next meeting ---
    next_meeting = (
        db.query(BoardMeeting)
        .filter(BoardMeeting.date >= today)
        .order_by(BoardMeeting.date.asc())
        .first()
    )

    # --- Compliance items due within 60 days ---
    deadline_60d = today + timedelta(days=60)
    compliance_items = (
        db.query(BylawComplianceItem)
        .filter(
            BylawComplianceItem.next_due <= deadline_60d,
            BylawComplianceItem.status != "completed",
        )
        .order_by(BylawComplianceItem.next_due.asc())
        .all()
    )

    # --- Grievance counts by facility (counts only — no details in agenda) ---
    open_grievances = (
        db.query(Grievance)
        .filter(Grievance.status.in_(["open", "pending_arbitration"]))
        .all()
    )
    grievance_counts: dict[str, int] = {}
    for g in open_grievances:
        grievance_counts[g.facility] = grievance_counts.get(g.facility, 0) + 1

    # --- Build context for AI prompt ---
    meeting_info = (
        f"Next meeting: {next_meeting.date.isoformat()} ({next_meeting.type})"
        if next_meeting
        else "No meeting scheduled yet"
    )

    compliance_text = ""
    if compliance_items:
        lines = [
            f"  - {c.requirement} (due {c.next_due.isoformat()}, "
            f"frequency: {c.frequency}, assigned: {c.assigned_to or 'unassigned'})"
            for c in compliance_items
        ]
        compliance_text = "Upcoming bylaw compliance items:\n" + "\n".join(lines)
    else:
        compliance_text = "No bylaw compliance items due in the next 60 days."

    grievance_text = ""
    if grievance_counts:
        lines = [f"  - {facility}: {count} open" for facility, count in grievance_counts.items()]
        grievance_text = "Open grievances by facility (counts only):\n" + "\n".join(lines)
    else:
        grievance_text = "No open grievances."

    prompt = (
        "Generate a structured Executive Board meeting agenda for CHCA District 1199NE AFSCME. "
        "Use standard union board meeting format with numbered agenda items. "
        "Do not include member names, grievance case numbers, or confidential details — "
        "use counts and categories only. "
        f"\n\n{meeting_info}"
        f"\n\n{compliance_text}"
        f"\n\n{grievance_text}"
        "\n\nInclude standard agenda sections: Call to Order, Roll Call/Quorum, "
        "Approval of Previous Minutes, Officers Reports, Grievance Report (counts by facility), "
        "Legislative Update, Compliance Calendar, New Business, Adjournment. "
        "Flag any compliance items or high grievance counts as requiring discussion."
    )

    response = await ai_router.complete(task="agenda_draft", prompt=prompt)

    return AgendaDraftResponse(
        meeting_date=next_meeting.date if next_meeting else None,
        generated_at=datetime.utcnow().isoformat() + "Z",
        draft=response.text,
        model_used=response.model_used,
        routed_to=response.routed_to,
    )
