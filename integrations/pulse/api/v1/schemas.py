"""Pydantic models for the /api/v1/agents/ endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Context endpoint  GET /api/v1/agents/context
# ---------------------------------------------------------------------------

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
# Phase 9b — Secretary/Treasurer context section
# ---------------------------------------------------------------------------

class FinanceContext(BaseModel):
    """SecTreas officer context bundle — finance section."""
    pending_cosignature_count: int = 0
    dues_arrears_facilities: list[str] = []
    ytd_disbursements: float = 0.0
    budget_variance_alert: bool = False


class SchedulingContext(BaseModel):
    """ExecSec officer context bundle — scheduling/minutes section."""
    pending_requests: int = 0
    minutes_drafts_in_progress: int = 0
    minutes_pending_approval: int = 0


# ---------------------------------------------------------------------------
# Phase 9a — Grievance context section — injected for President agent
# ---------------------------------------------------------------------------

class GrievanceDeadlineItem(BaseModel):
    case_number: str
    facility: str
    deadline_type: str
    days_remaining: int
    status: str


class GrievanceContext(BaseModel):
    open_count: int = 0
    approaching_deadline: list[GrievanceDeadlineItem] = []


# ---------------------------------------------------------------------------
# Phase 9a — Board context section — injected for President agent
# ---------------------------------------------------------------------------

class NextMeetingContext(BaseModel):
    date: str
    type: str
    days_away: int


class BoardContext(BaseModel):
    next_meeting: Optional[NextMeetingContext] = None
    compliance_items_due_30d: int = 0


class AgentContextResponse(BaseModel):
    owner_id: str
    generated_at: str
    calendar: CalendarContext
    tasks: TaskContext
    email: EmailContext
    # Phase 9b — Officer-specific context sections (None for non-officers / wrong role)
    finance: Optional[FinanceContext] = None
    scheduling: Optional[SchedulingContext] = None
    # Phase 9a — President-specific context sections
    grievances: Optional[GrievanceContext] = None
    board: Optional[BoardContext] = None


# ---------------------------------------------------------------------------
# Check-in endpoint  POST /api/v1/agents/checkin
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Check-in status  GET /api/v1/agents/checkin/status
# ---------------------------------------------------------------------------

class CheckinSlotStatus(BaseModel):
    completed: bool = False
    time: Optional[str] = None
    scheduled_for: Optional[str] = None


class CheckinStatusResponse(BaseModel):
    morning: CheckinSlotStatus
    evening: CheckinSlotStatus


# ---------------------------------------------------------------------------
# Capture endpoint  POST /api/v1/agents/capture
# ---------------------------------------------------------------------------

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
