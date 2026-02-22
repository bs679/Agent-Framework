"""Role-based context bundle assembly for GET /api/v1/agents/context.

Design
------
``build_context()`` is the single entry point.  It assembles the
AgentContextResponse by calling a set of *section providers* — small
functions that each return one section of the bundle.

Adding a new section later is a one-liner: write a section provider and
register it in the ``_SECTION_REGISTRY`` at the bottom of this module.

Role routing
------------
Four distinct context profiles are assembled:

  ADMIN / president
    Base + compliance (ADMIN-filtered) + grievances + board +
    finance_summary (count only) + legislative

  OFFICER / sectreasurer
    Base + compliance (OFFICER-filtered) + finance (full detail) +
    minutes_pending

  OFFICER / execsecretary
    Base + compliance (OFFICER-filtered) + scheduling + minutes

  STAFF / staff
    Base + compliance (STAFF/ALL filtered) — nothing sensitive
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import (
    AgentContextResponse,
    BoardSection,
    CalendarContext,
    CalendarEvent,
    ComplianceContext,
    ComplianceNextItem,
    EmailContext,
    FinanceDetailSection,
    FinanceSummarySection,
    GrievanceItem,
    GrievancesSection,
    LegislativeSection,
    MinutesDraftSection,
    MinutesPendingSection,
    SchedulingSection,
    TaskContext,
    TaskItem,
)
from integrations.pulse.core.executive_guard import sanitize_event
from integrations.pulse.core.models import ComplianceItem


# ---------------------------------------------------------------------------
# Stub data providers — replace with real Pulse DB / MS Graph queries later
# ---------------------------------------------------------------------------

def _stub_calendar_events() -> list[dict[str, Any]]:
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
# Base section providers (all roles)
# ---------------------------------------------------------------------------

def _build_calendar() -> CalendarContext:
    today_raw = _stub_calendar_events()
    upcoming_raw = _stub_upcoming_events()
    return CalendarContext(
        today=[CalendarEvent(**sanitize_event(evt)) for evt in today_raw],
        upcoming_48h=[CalendarEvent(**sanitize_event(evt)) for evt in upcoming_raw],
    )


def _build_tasks() -> TaskContext:
    data = _stub_tasks()
    return TaskContext(
        overdue=data["overdue"],
        due_today=data["due_today"],
        high_priority=data["high_priority"],
        items=[TaskItem(**t) for t in data["items"]],
    )


def _build_email() -> EmailContext:
    return EmailContext(**_stub_email())


def _build_compliance(db: Session, role: str, role_detail: str) -> ComplianceContext:
    """Return a compliance summary filtered to the user's role.

    Role filter logic:
      ADMIN    → items where assigned_to_role IN ('ADMIN', 'ALL')
      OFFICER  → items where assigned_to_role IN ('OFFICER', 'ALL')
      STAFF    → items where assigned_to_role IN ('STAFF', 'ALL')
    """
    allowed_roles = {role, "ALL"}

    today = date.today()
    thirty_days = date.fromordinal(today.toordinal() + 30)

    all_items = (
        db.query(ComplianceItem)
        .filter(ComplianceItem.assigned_to_role.in_(list(allowed_roles)))
        .all()
    )

    # Refresh statuses in-memory (don't write back during context build)
    for item in all_items:
        item.refresh_status()

    overdue_count = sum(1 for i in all_items if i.status == "overdue")
    due_30d = [
        i for i in all_items
        if i.next_due is not None and today <= i.next_due <= thirty_days
    ]

    next_item: Optional[ComplianceNextItem] = None
    upcoming = sorted(
        [i for i in all_items if i.next_due is not None and i.next_due >= today],
        key=lambda i: i.next_due,
    )
    if upcoming:
        nxt = upcoming[0]
        days = (nxt.next_due - today).days
        next_item = ComplianceNextItem(
            title=nxt.title,
            due_date=nxt.next_due.isoformat(),
            days_away=days,
            assigned_to_role=nxt.assigned_to_role,
        )

    return ComplianceContext(
        items_due_30d=len(due_30d),
        overdue_count=overdue_count,
        next_item=next_item,
    )


# ---------------------------------------------------------------------------
# Officer / admin section providers (stubs — wire to real data in Phase 10)
# ---------------------------------------------------------------------------

def _build_grievances() -> GrievancesSection:
    """ADMIN only. Stub: replace with real grievance DB query."""
    return GrievancesSection(
        open_count=7,
        deadline_within_7d=2,
        items=[
            GrievanceItem(
                id="GR-2024-117",
                site="Waterbury Hospital",
                article="Art. 12 — Discipline",
                deadline_days=3,
                status="step_2",
            ),
            GrievanceItem(
                id="GR-2024-089",
                site="Norwalk Hospital",
                article="Art. 8 — Scheduling",
                deadline_days=6,
                status="step_1",
            ),
        ],
    )


def _build_board() -> BoardSection:
    """ADMIN only. Stub: replace with calendar/DB query."""
    return BoardSection(
        next_meeting_date="2026-04-01",
        pending_agenda_items=3,
        quorum_confirmed=False,
    )


def _build_finance_summary() -> FinanceSummarySection:
    """ADMIN only — count of pending disbursements, no amounts."""
    return FinanceSummarySection(pending_disbursements=4)


def _build_legislative() -> LegislativeSection:
    """ADMIN only. Stub: replace with legislative tracker API."""
    return LegislativeSection(
        tracked_bills=5,
        hearings_this_week=1,
        action_required=2,
    )


def _build_finance_detail() -> FinanceDetailSection:
    """OFFICER SecTreas only — full financial detail."""
    return FinanceDetailSection(
        pending_disbursements=4,
        pending_amount_usd=12_450.00,
        dues_collected_mtd=8_230.50,
        budget_variance_pct=-2.3,
    )


def _build_minutes_pending() -> MinutesPendingSection:
    """OFFICER SecTreas only — minutes awaiting approval."""
    return MinutesPendingSection(pending_approval_count=1)


def _build_scheduling() -> SchedulingSection:
    """OFFICER ExecSec only."""
    return SchedulingSection(
        pending_scheduling_requests=3,
        upcoming_correspondence_deadlines=1,
    )


def _build_minutes_draft() -> MinutesDraftSection:
    """OFFICER ExecSec only — minutes in draft."""
    return MinutesDraftSection(drafts_in_progress=1, overdue_drafts=0)


# ---------------------------------------------------------------------------
# Main context builder
# ---------------------------------------------------------------------------

def build_context(
    owner_id: str,
    role: str,
    role_detail: str,
    db: Session,
) -> AgentContextResponse:
    """Assemble the full agent context bundle for the given user.

    Parameters
    ----------
    owner_id:    Azure AD user ID / preferred_username
    role:        Top-level role — 'ADMIN', 'OFFICER', or 'STAFF'
    role_detail: Sub-role — 'president', 'sectreasurer', 'execsecretary', 'staff'
    db:          Active SQLAlchemy session (for compliance query)
    """
    base = dict(
        owner_id=owner_id,
        generated_at=datetime.utcnow().isoformat() + "Z",
        role=role,
        role_detail=role_detail,
        calendar=_build_calendar(),
        tasks=_build_tasks(),
        email=_build_email(),
        compliance=_build_compliance(db, role, role_detail),
    )

    # ── ADMIN (President) ──────────────────────────────────────────────────
    if role == "ADMIN":
        return AgentContextResponse(
            **base,
            grievances=_build_grievances(),
            board=_build_board(),
            finance_summary=_build_finance_summary(),
            legislative=_build_legislative(),
        )

    # ── OFFICER SecTreas ───────────────────────────────────────────────────
    if role == "OFFICER" and role_detail == "sectreasurer":
        return AgentContextResponse(
            **base,
            finance=_build_finance_detail(),
            minutes_pending=_build_minutes_pending(),
        )

    # ── OFFICER ExecSec ────────────────────────────────────────────────────
    if role == "OFFICER" and role_detail == "execsecretary":
        return AgentContextResponse(
            **base,
            scheduling=_build_scheduling(),
            minutes=_build_minutes_draft(),
        )

    # ── STAFF (and any unrecognised officer sub-role fallback) ─────────────
    return AgentContextResponse(**base)
