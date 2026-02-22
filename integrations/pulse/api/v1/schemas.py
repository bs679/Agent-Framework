"""Pydantic models for the /api/v1/agents/, /api/v1/compliance/, and
/api/v1/admin/ endpoints."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ===========================================================================
# Context endpoint  GET /api/v1/agents/context
# ===========================================================================

class CalendarEvent(BaseModel):
    title: str
    time: str = Field(..., description="HH:MM format")
    duration_minutes: int
    location: Optional[str] = None
    attendees_count: int = 0
    is_executive_session: bool = False


class CalendarContext(BaseModel):
    today: list[CalendarEvent] = []
    upcoming_48h: list[CalendarEvent] = []


class TaskItem(BaseModel):
    id: str
    title: str
    due_date: Optional[str] = None
    priority: str = "medium"


class TaskContext(BaseModel):
    overdue: int = 0
    due_today: int = 0
    high_priority: int = 0
    items: list[TaskItem] = []


class EmailContext(BaseModel):
    unread_count: int = 0
    urgent_count: int = 0


# ---------------------------------------------------------------------------
# Compliance context (included in ALL agent context bundles, role-filtered)
# ---------------------------------------------------------------------------

class ComplianceNextItem(BaseModel):
    title: str
    due_date: str  # ISO date string
    days_away: int
    assigned_to_role: str


class ComplianceContext(BaseModel):
    """Summary of compliance obligations for the agent context bundle."""
    items_due_30d: int = 0
    overdue_count: int = 0
    next_item: Optional[ComplianceNextItem] = None


# ---------------------------------------------------------------------------
# Officer / admin role-specific sections (stub values in dev)
# ---------------------------------------------------------------------------

class GrievanceItem(BaseModel):
    id: str
    site: str
    article: str
    deadline_days: int
    status: str


class GrievancesSection(BaseModel):
    """ADMIN role only (President)."""
    open_count: int = 0
    deadline_within_7d: int = 0
    items: list[GrievanceItem] = []


class BoardSection(BaseModel):
    """ADMIN role only (President)."""
    next_meeting_date: Optional[str] = None
    pending_agenda_items: int = 0
    quorum_confirmed: bool = False


class FinanceSummarySection(BaseModel):
    """ADMIN role — pending disbursements total count only (no amounts)."""
    pending_disbursements: int = 0


class FinanceDetailSection(BaseModel):
    """OFFICER SecTreas role — full finance detail."""
    pending_disbursements: int = 0
    pending_amount_usd: float = 0.0
    dues_collected_mtd: float = 0.0
    budget_variance_pct: float = 0.0


class LegislativeSection(BaseModel):
    """ADMIN role only (President)."""
    tracked_bills: int = 0
    hearings_this_week: int = 0
    action_required: int = 0


class MinutesPendingSection(BaseModel):
    """OFFICER SecTreas role — minutes awaiting approval."""
    pending_approval_count: int = 0


class SchedulingSection(BaseModel):
    """OFFICER ExecSec role."""
    pending_scheduling_requests: int = 0
    upcoming_correspondence_deadlines: int = 0


class MinutesDraftSection(BaseModel):
    """OFFICER ExecSec role — minutes in draft."""
    drafts_in_progress: int = 0
    overdue_drafts: int = 0


# ---------------------------------------------------------------------------
# Main context response — sections are Optional; absent = not authorized
# ---------------------------------------------------------------------------

class AgentContextResponse(BaseModel):
    owner_id: str
    generated_at: str
    role: str
    role_detail: str

    # Base context — all roles
    calendar: CalendarContext
    tasks: TaskContext
    email: EmailContext
    compliance: ComplianceContext

    # ADMIN only
    grievances: Optional[GrievancesSection] = None
    board: Optional[BoardSection] = None
    finance_summary: Optional[FinanceSummarySection] = None
    legislative: Optional[LegislativeSection] = None

    # OFFICER SecTreas only
    finance: Optional[FinanceDetailSection] = None
    minutes_pending: Optional[MinutesPendingSection] = None

    # OFFICER ExecSec only
    scheduling: Optional[SchedulingSection] = None
    minutes: Optional[MinutesDraftSection] = None


# ===========================================================================
# Check-in endpoint  POST /api/v1/agents/checkin
# ===========================================================================

class AlertType(str, Enum):
    deadline = "deadline"
    urgent_email = "urgent_email"
    task_overdue = "task_overdue"
    custom = "custom"


class AlertPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CheckinAlert(BaseModel):
    type: AlertType
    message: str
    priority: AlertPriority = AlertPriority.medium


class CheckinType(str, Enum):
    morning = "morning"
    evening = "evening"


class CheckinRequest(BaseModel):
    agent_id: str
    checkin_type: CheckinType
    timestamp: str
    summary: str
    alerts: list[CheckinAlert] = []


class CheckinResponse(BaseModel):
    status: str = "accepted"
    checkin_id: str


# ===========================================================================
# Check-in status  GET /api/v1/agents/checkin/status
# ===========================================================================

class CheckinSlotStatus(BaseModel):
    completed: bool = False
    time: Optional[str] = None
    scheduled_for: Optional[str] = None


class CheckinStatusResponse(BaseModel):
    morning: CheckinSlotStatus
    evening: CheckinSlotStatus


# ===========================================================================
# Capture endpoint  POST /api/v1/agents/capture
# ===========================================================================

class CaptureContext(str, Enum):
    manual = "manual"
    email = "email"
    calendar = "calendar"
    task = "task"


class SuggestedAction(str, Enum):
    create_task = "create_task"
    add_to_memory = "add_to_memory"
    reply_email = "reply_email"
    flag_for_review = "flag_for_review"


class CaptureRequest(BaseModel):
    agent_id: str
    content: str
    context: CaptureContext = CaptureContext.manual


class CaptureResponse(BaseModel):
    suggested_action: SuggestedAction
    details: str


# ===========================================================================
# Compliance endpoints  /api/v1/compliance/
# ===========================================================================

class ComplianceItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    frequency: str
    last_completed: Optional[str] = None  # ISO date
    next_due: Optional[str] = None        # ISO date
    assigned_to_role: str
    status: str
    notes: Optional[str] = None
    days_until_due: Optional[int] = None


class ComplianceListResponse(BaseModel):
    items: list[ComplianceItemResponse]
    total: int


class CompleteComplianceRequest(BaseModel):
    completed_date: Optional[str] = Field(
        default=None,
        description="ISO date of completion; defaults to today if omitted",
    )
    notes: Optional[str] = None


class CompleteComplianceResponse(BaseModel):
    id: int
    status: str
    last_completed: str
    next_due: Optional[str]
    message: str


# ===========================================================================
# Admin endpoints  /api/v1/admin/
# ===========================================================================

class RoleDetailRequest(BaseModel):
    role_detail: str = Field(
        ...,
        description=(
            "Sub-role for the user: president | sectreasurer | execsecretary | staff"
        ),
    )
    role: Optional[str] = Field(
        default=None,
        description="Top-level role: ADMIN | OFFICER | STAFF (inferred from role_detail if omitted)",
    )
    display_name: Optional[str] = None
    email: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    role: str
    role_detail: str
    display_name: Optional[str]
    email: Optional[str]
    message: str
