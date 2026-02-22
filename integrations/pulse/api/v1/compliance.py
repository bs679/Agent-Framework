"""Compliance calendar endpoints for Pulse.

All endpoints live under /api/v1/compliance/ and require Azure AD JWT
authentication.  Items are filtered by the authenticated user's role.

Endpoints
---------
GET  /api/v1/compliance/            — list items for the user's role
GET  /api/v1/compliance/upcoming    — items due within ?days= (default 30)
PATCH /api/v1/compliance/{id}/complete — mark an item completed, advance next_due
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import (
    CompleteComplianceRequest,
    CompleteComplianceResponse,
    ComplianceItemResponse,
    ComplianceListResponse,
)
from integrations.pulse.core.auth import get_current_user_with_role
from integrations.pulse.core.database import get_db
from integrations.pulse.core.models import ComplianceFrequency, ComplianceItem

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed_roles(role: str) -> list[str]:
    """Return the assigned_to_role values visible to the given top-level role."""
    return [role, "ALL"]


def _item_to_response(item: ComplianceItem) -> ComplianceItemResponse:
    """Convert an ORM model to the API response schema."""
    item.refresh_status()
    return ComplianceItemResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        category=item.category,
        frequency=item.frequency,
        last_completed=item.last_completed.isoformat() if item.last_completed else None,
        next_due=item.next_due.isoformat() if item.next_due else None,
        assigned_to_role=item.assigned_to_role,
        status=item.status,
        notes=item.notes,
        days_until_due=item.days_until_due(),
    )


def _advance_next_due(item: ComplianceItem, completed_date: date) -> Optional[date]:
    """Calculate the next due date after marking an item completed.

    Advances forward from the later of ``completed_date`` and the existing
    ``item.next_due`` so that completing an item early doesn't produce a
    next_due that is still in the past or equal to the current value.
    """
    freq = item.frequency
    # Advance from the existing next_due if it's >= completed_date, so that
    # marking an item complete before its due date still advances a full cycle.
    base = max(completed_date, item.next_due) if item.next_due else completed_date

    if freq == ComplianceFrequency.monthly.value:
        # First day of the month after base
        next_month = (base.replace(day=1) + timedelta(days=32)).replace(day=1)
        return next_month

    if freq == ComplianceFrequency.quarterly.value:
        for month in (1, 4, 7, 10):
            if base.month < month:
                return date(base.year, month, 1)
        return date(base.year + 1, 1, 1)

    if freq == ComplianceFrequency.annual.value:
        # Same month/day one year after base
        if item.next_due:
            return item.next_due.replace(year=base.year + 1)
        return date(base.year + 1, base.month, base.day)

    # one_time — no next due
    return None


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/
# ---------------------------------------------------------------------------

@router.get("/", response_model=ComplianceListResponse)
async def list_compliance_items(
    user: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> ComplianceListResponse:
    """Return all compliance items visible to the authenticated user's role."""
    role: str = user["role"]
    allowed = _allowed_roles(role)

    items = (
        db.query(ComplianceItem)
        .filter(ComplianceItem.assigned_to_role.in_(allowed))
        .order_by(ComplianceItem.next_due.asc().nulls_last())
        .all()
    )

    return ComplianceListResponse(
        items=[_item_to_response(i) for i in items],
        total=len(items),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/compliance/upcoming
# ---------------------------------------------------------------------------

@router.get("/upcoming", response_model=ComplianceListResponse)
async def list_upcoming_compliance(
    days: int = Query(default=30, ge=1, le=365, description="Horizon in days"),
    user: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> ComplianceListResponse:
    """Return compliance items due within the next *days* days."""
    role: str = user["role"]
    allowed = _allowed_roles(role)

    today = date.today()
    horizon = today + timedelta(days=days)

    items = (
        db.query(ComplianceItem)
        .filter(
            ComplianceItem.assigned_to_role.in_(allowed),
            ComplianceItem.next_due >= today,
            ComplianceItem.next_due <= horizon,
        )
        .order_by(ComplianceItem.next_due.asc())
        .all()
    )

    return ComplianceListResponse(
        items=[_item_to_response(i) for i in items],
        total=len(items),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/compliance/{id}/complete
# ---------------------------------------------------------------------------

@router.patch("/{item_id}/complete", response_model=CompleteComplianceResponse)
async def complete_compliance_item(
    item_id: int,
    body: CompleteComplianceRequest,
    user: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> CompleteComplianceResponse:
    """Mark a compliance item as completed and advance its next_due date.

    The caller must have the appropriate role to see/own the item.
    Attempting to complete an item outside your role returns 404.
    """
    role: str = user["role"]
    allowed = _allowed_roles(role)

    item: Optional[ComplianceItem] = (
        db.query(ComplianceItem)
        .filter(
            ComplianceItem.id == item_id,
            ComplianceItem.assigned_to_role.in_(allowed),
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance item {item_id} not found or not accessible for your role.",
        )

    completed_date = date.today()
    if body.completed_date:
        try:
            completed_date = date.fromisoformat(body.completed_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="completed_date must be ISO format (YYYY-MM-DD)",
            )

    item.last_completed = completed_date
    item.next_due = _advance_next_due(item, completed_date)
    item.status = "completed"
    if body.notes:
        item.notes = body.notes

    db.commit()
    db.refresh(item)

    return CompleteComplianceResponse(
        id=item.id,
        status=item.status,
        last_completed=item.last_completed.isoformat(),
        next_due=item.next_due.isoformat() if item.next_due else None,
        message=f"'{item.title}' marked complete. Next due: {item.next_due or 'N/A'}.",
    )
