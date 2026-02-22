"""Module 1 — Grievance Intelligence endpoints.

All endpoints require a valid Azure AD JWT.

Routes:
  GET    /api/v1/grievances            — List with filters
  POST   /api/v1/grievances            — Create
  GET    /api/v1/grievances/dashboard  — Aggregate counts by facility + status
  GET    /api/v1/grievances/{id}       — Detail
  PATCH  /api/v1/grievances/{id}       — Update status / notes

Deadline calculation:
  Step 1: filed_date + 10 business days
  Step 2: step1_deadline + 15 business days
  Arbitration: step2_deadline + ARBITRATION_DAYS (default 30, configurable via
               GRIEVANCE_ARBITRATION_DAYS env var)
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.business_days import add_business_days, days_until
from integrations.pulse.db.models.grievance import (
    Grievance,
    GrievanceAlert,
    GrievanceEvent,
)
from integrations.pulse.db.session import get_db

router = APIRouter(prefix="/api/v1/grievances", tags=["grievances"])

ARBITRATION_DAYS: int = int(os.environ.get("GRIEVANCE_ARBITRATION_DAYS", "30"))

# ---------------------------------------------------------------------------
# Allowed values (validated at the Pydantic layer)
# ---------------------------------------------------------------------------
VALID_FACILITIES = {"Bradley", "Norwalk", "Waterbury", "Region12", "Region13", "Region17"}
VALID_STATUSES = {"open", "pending_arbitration", "closed", "withdrawn"}
VALID_TYPES = {"discipline", "contract_violation", "working_conditions", "other"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GrievanceCreate(BaseModel):
    case_number: str = Field(..., max_length=50)
    facility: str
    type: str
    filed_date: date
    notes: Optional[str] = None

    def validate_enums(self) -> None:
        if self.facility not in VALID_FACILITIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"facility must be one of: {sorted(VALID_FACILITIES)}",
            )
        if self.type not in VALID_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"type must be one of: {sorted(VALID_TYPES)}",
            )


class GrievancePatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None


class GrievanceEventCreate(BaseModel):
    event_type: str = Field(..., max_length=60)
    event_date: date
    notes: Optional[str] = None


class GrievanceEventOut(BaseModel):
    id: int
    event_type: str
    event_date: date
    notes: Optional[str]
    created_by: str

    model_config = {"from_attributes": True}


class GrievanceOut(BaseModel):
    id: int
    case_number: str
    facility: str
    status: str
    type: str
    filed_date: date
    step1_deadline: date
    step2_deadline: date
    arbitration_deadline: date
    outcome: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    events: list[GrievanceEventOut] = []

    model_config = {"from_attributes": True}


class ApproachingDeadline(BaseModel):
    case_number: str
    facility: str
    deadline_type: str
    days_remaining: int
    status: str


class GrievanceDashboard(BaseModel):
    by_facility: dict[str, dict[str, int]]
    by_status: dict[str, int]
    total_open: int
    approaching_deadlines: list[ApproachingDeadline]


# ---------------------------------------------------------------------------
# Helper: compute deadlines from filed_date
# ---------------------------------------------------------------------------

def _compute_deadlines(filed_date: date) -> tuple[date, date, date]:
    step1 = add_business_days(filed_date, 10)
    step2 = add_business_days(step1, 15)
    arb = add_business_days(step2, ARBITRATION_DAYS)
    return step1, step2, arb


def _approaching(grievances: list[Grievance], window: int = 7) -> list[ApproachingDeadline]:
    results = []
    today = date.today()
    for g in grievances:
        if g.status not in ("open", "pending_arbitration"):
            continue
        for dtype, ddate in [
            ("step1", g.step1_deadline),
            ("step2", g.step2_deadline),
            ("arbitration", g.arbitration_deadline),
        ]:
            remaining = days_until(ddate, today)
            if 0 <= remaining <= window:
                results.append(
                    ApproachingDeadline(
                        case_number=g.case_number,
                        facility=g.facility,
                        deadline_type=dtype,
                        days_remaining=remaining,
                        status=g.status,
                    )
                )
    results.sort(key=lambda a: a.days_remaining)
    return results


# ---------------------------------------------------------------------------
# GET /api/v1/grievances/dashboard  (must appear BEFORE /{id} route)
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=GrievanceDashboard)
def get_grievance_dashboard(
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrievanceDashboard:
    """Aggregate counts by facility and status, plus approaching deadlines."""
    all_grievances: list[Grievance] = db.query(Grievance).all()

    by_facility: dict[str, dict[str, int]] = {}
    by_status: dict[str, int] = {}
    total_open = 0

    for g in all_grievances:
        # by_facility
        fac = by_facility.setdefault(g.facility, {})
        fac[g.status] = fac.get(g.status, 0) + 1

        # by_status
        by_status[g.status] = by_status.get(g.status, 0) + 1

        if g.status in ("open", "pending_arbitration"):
            total_open += 1

    approaching = _approaching(all_grievances)

    return GrievanceDashboard(
        by_facility=by_facility,
        by_status=by_status,
        total_open=total_open,
        approaching_deadlines=approaching,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/grievances
# ---------------------------------------------------------------------------

@router.get("", response_model=list[GrievanceOut])
def list_grievances(
    facility: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    approaching_deadline: bool = Query(False, description="Only show grievances with a deadline within 7 days"),
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GrievanceOut]:
    """List grievances with optional filters."""
    q = db.query(Grievance)
    if facility:
        q = q.filter(Grievance.facility == facility)
    if status:
        q = q.filter(Grievance.status == status)

    grievances = q.order_by(Grievance.filed_date.desc()).all()

    if approaching_deadline:
        today = date.today()
        grievances = [
            g for g in grievances
            if g.status in ("open", "pending_arbitration") and any(
                0 <= days_until(d, today) <= 7
                for d in [g.step1_deadline, g.step2_deadline, g.arbitration_deadline]
            )
        ]

    return [GrievanceOut.model_validate(g) for g in grievances]


# ---------------------------------------------------------------------------
# POST /api/v1/grievances
# ---------------------------------------------------------------------------

@router.post("", response_model=GrievanceOut, status_code=status.HTTP_201_CREATED)
def create_grievance(
    body: GrievanceCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrievanceOut:
    """Create a new grievance. Deadlines are auto-calculated from filed_date."""
    body.validate_enums()

    # Check for duplicate case number
    existing = db.query(Grievance).filter(Grievance.case_number == body.case_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Grievance with case_number '{body.case_number}' already exists",
        )

    step1, step2, arb = _compute_deadlines(body.filed_date)

    g = Grievance(
        case_number=body.case_number,
        facility=body.facility,
        status="open",
        type=body.type,
        filed_date=body.filed_date,
        step1_deadline=step1,
        step2_deadline=step2,
        arbitration_deadline=arb,
        notes=body.notes,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return GrievanceOut.model_validate(g)


# ---------------------------------------------------------------------------
# GET /api/v1/grievances/{id}
# ---------------------------------------------------------------------------

@router.get("/{grievance_id}", response_model=GrievanceOut)
def get_grievance(
    grievance_id: int,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrievanceOut:
    """Return full detail for a single grievance including its event log."""
    g = db.query(Grievance).filter(Grievance.id == grievance_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")
    return GrievanceOut.model_validate(g)


# ---------------------------------------------------------------------------
# PATCH /api/v1/grievances/{id}
# ---------------------------------------------------------------------------

@router.patch("/{grievance_id}", response_model=GrievanceOut)
def update_grievance(
    grievance_id: int,
    body: GrievancePatch,
    _user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrievanceOut:
    """Update status, notes, or outcome on an existing grievance."""
    g = db.query(Grievance).filter(Grievance.id == grievance_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")

    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be one of: {sorted(VALID_STATUSES)}",
            )
        g.status = body.status
    if body.notes is not None:
        g.notes = body.notes
    if body.outcome is not None:
        g.outcome = body.outcome

    g.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(g)
    return GrievanceOut.model_validate(g)
