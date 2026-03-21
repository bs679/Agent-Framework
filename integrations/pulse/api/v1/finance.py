"""Finance module API — Secretary/Treasurer officer capability.

Endpoints at /api/v1/finance/:

  GET  /dashboard               — YTD summary + budget overview
  GET  /disbursements           — list (filter by status)
  POST /disbursements           — create (starts at pending_first_sig)
  GET  /disbursements/{id}      — detail
  POST /disbursements/{id}/sign — co-signature enforcement
  GET  /dues-remittances        — list by facility and period
  POST /dues-remittances        — record received remittance
  GET  /dues-remittances/arrears — facilities with missing/partial dues
  GET  /audit                   — full audit log (admin) or per-disbursement

Co-signature hard rules (from CLAUDE.md):
  1. Requestor cannot be first signer (no self-approval).
  2. Second signer must be a DIFFERENT officer than the first signer.
  3. A disbursement with only one signature CANNOT be executed.
  4. Every state change is logged to disbursement_audit.

All endpoints require a valid JWT (via get_current_user).
Sign and approve endpoints additionally require OFFICER role.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from integrations.pulse.core.auth import get_current_user
from integrations.pulse.core.roles import require_officer
from integrations.pulse.db.models.finance import (
    BudgetLine,
    Disbursement,
    DisbursementAudit,
    DuesRemittance,
)
from integrations.pulse.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class DisbursementCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payee: str
    description: str
    category: str
    notes: Optional[str] = None


class DisbursementSignRequest(BaseModel):
    signature_role: str = Field(..., pattern="^(first|second)$")
    approved: bool


class DisbursementOut(BaseModel):
    id: int
    amount: float
    payee: str
    description: str
    category: str
    requested_by: str
    requested_at: str
    status: str
    first_signature_by: Optional[str]
    first_signature_at: Optional[str]
    second_signature_by: Optional[str]
    second_signature_at: Optional[str]
    approved_at: Optional[str]
    check_number: Optional[str]
    notes: Optional[str]


class DuesRemittanceCreate(BaseModel):
    facility: str
    period: str = Field(..., description="YYYY-MM format")
    expected_amount: float = Field(..., ge=0)
    received_amount: float = Field(default=0.0, ge=0)
    received_date: Optional[str] = None
    notes: Optional[str] = None


class DuesRemittanceOut(BaseModel):
    id: int
    facility: str
    period: str
    expected_amount: float
    received_amount: float
    received_date: Optional[str]
    reconciled: bool
    notes: Optional[str]


class AuditEntryOut(BaseModel):
    id: int
    disbursement_id: int
    action: str
    performed_by: str
    performed_at: str
    previous_status: Optional[str]
    new_status: str
    notes: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CURRENT_FISCAL_YEAR = "2025-2026"
_CURRENT_PERIOD = datetime.now(timezone.utc).strftime("%Y-%m")


def _dt_str(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _disbursement_out(d: Disbursement) -> DisbursementOut:
    return DisbursementOut(
        id=d.id,
        amount=d.amount,
        payee=d.payee,
        description=d.description,
        category=d.category,
        requested_by=d.requested_by,
        requested_at=_dt_str(d.requested_at) or "",
        status=d.status,
        first_signature_by=d.first_signature_by,
        first_signature_at=_dt_str(d.first_signature_at),
        second_signature_by=d.second_signature_by,
        second_signature_at=_dt_str(d.second_signature_at),
        approved_at=_dt_str(d.approved_at),
        check_number=d.check_number,
        notes=d.notes,
    )


def _dues_out(r: DuesRemittance) -> DuesRemittanceOut:
    return DuesRemittanceOut(
        id=r.id,
        facility=r.facility,
        period=r.period,
        expected_amount=r.expected_amount,
        received_amount=r.received_amount,
        received_date=_dt_str(r.received_date),
        reconciled=r.reconciled,
        notes=r.notes,
    )


def _audit_out(a: DisbursementAudit) -> AuditEntryOut:
    return AuditEntryOut(
        id=a.id,
        disbursement_id=a.disbursement_id,
        action=a.action,
        performed_by=a.performed_by,
        performed_at=_dt_str(a.performed_at) or "",
        previous_status=a.previous_status,
        new_status=a.new_status,
        notes=a.notes,
    )


def _write_audit(
    db: Session,
    disbursement_id: int,
    action: str,
    performed_by: str,
    previous_status: str | None,
    new_status: str,
    notes: str | None = None,
) -> None:
    """Append an immutable entry to the disbursement_audit table."""
    entry = DisbursementAudit(
        disbursement_id=disbursement_id,
        action=action,
        performed_by=performed_by,
        performed_at=datetime.now(timezone.utc),
        previous_status=previous_status,
        new_status=new_status,
        notes=notes,
    )
    db.add(entry)


# ---------------------------------------------------------------------------
# GET /api/v1/finance/dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
async def finance_dashboard(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """YTD financial summary for the SecTreas dashboard."""
    # YTD disbursements (approved only, current fiscal year)
    all_disbursements = db.query(Disbursement).all()
    approved = [d for d in all_disbursements if d.status == "approved"]
    ytd_total = sum(d.amount for d in approved)

    pending = [
        d for d in all_disbursements
        if d.status in ("pending_first_sig", "pending_second_sig")
    ]

    # Budget lines for current fiscal year
    budget_lines = (
        db.query(BudgetLine)
        .filter(BudgetLine.fiscal_year == _CURRENT_FISCAL_YEAR)
        .all()
    )
    total_budgeted = sum(bl.budgeted_amount for bl in budget_lines)
    budget_remaining = total_budgeted - ytd_total

    budget_variance_alert = any(
        bl.actual_amount > bl.budgeted_amount for bl in budget_lines
    )

    # Dues arrears: remittances for current period that are not fully received
    current_remittances = (
        db.query(DuesRemittance)
        .filter(DuesRemittance.period == _CURRENT_PERIOD)
        .all()
    )
    arrears_count = sum(
        1 for r in current_remittances
        if r.received_amount < r.expected_amount and not r.reconciled
    )

    budget_line_out = []
    for bl in budget_lines:
        variance_pct = (
            round((bl.actual_amount - bl.budgeted_amount) / bl.budgeted_amount * 100, 2)
            if bl.budgeted_amount else 0.0
        )
        budget_line_out.append({
            "category": bl.category,
            "budgeted": bl.budgeted_amount,
            "actual": bl.actual_amount,
            "variance_pct": variance_pct,
        })

    return {
        "fiscal_year": _CURRENT_FISCAL_YEAR,
        "ytd_disbursements": round(ytd_total, 2),
        "budget_remaining": round(budget_remaining, 2),
        "pending_disbursements": len(pending),
        "dues_arrears_count": arrears_count,
        "budget_lines": budget_line_out,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/finance/disbursements
# ---------------------------------------------------------------------------


@router.get("/disbursements", response_model=list[DisbursementOut])
async def list_disbursements(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DisbursementOut]:
    q = db.query(Disbursement)
    if status_filter:
        q = q.filter(Disbursement.status == status_filter)
    return [_disbursement_out(d) for d in q.order_by(Disbursement.requested_at.desc()).all()]


# ---------------------------------------------------------------------------
# POST /api/v1/finance/disbursements
# ---------------------------------------------------------------------------


@router.post("/disbursements", response_model=DisbursementOut, status_code=201)
async def create_disbursement(
    body: DisbursementCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisbursementOut:
    """Create a disbursement request. Status starts at pending_first_sig."""
    now = datetime.now(timezone.utc)
    d = Disbursement(
        amount=body.amount,
        payee=body.payee,
        description=body.description,
        category=body.category,
        requested_by=user["user_id"],
        requested_at=now,
        status="pending_first_sig",
        notes=body.notes,
    )
    db.add(d)
    db.flush()  # get id before audit

    _write_audit(
        db,
        disbursement_id=d.id,
        action="create",
        performed_by=user["user_id"],
        previous_status=None,
        new_status="pending_first_sig",
        notes=f"Created by {user['user_id']}",
    )
    db.commit()
    db.refresh(d)
    return _disbursement_out(d)


# ---------------------------------------------------------------------------
# GET /api/v1/finance/disbursements/{id}
# ---------------------------------------------------------------------------


@router.get("/disbursements/{disbursement_id}", response_model=DisbursementOut)
async def get_disbursement(
    disbursement_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisbursementOut:
    d = db.query(Disbursement).filter(Disbursement.id == disbursement_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Disbursement not found")
    return _disbursement_out(d)


# ---------------------------------------------------------------------------
# POST /api/v1/finance/disbursements/{id}/sign
# ---------------------------------------------------------------------------


@router.post("/disbursements/{disbursement_id}/sign", response_model=DisbursementOut)
async def sign_disbursement(
    disbursement_id: int,
    body: DisbursementSignRequest,
    user: dict[str, Any] = Depends(require_officer),
    db: Session = Depends(get_db),
) -> DisbursementOut:
    """Apply an officer co-signature to a disbursement.

    Hard rules enforced here (non-negotiable per CLAUDE.md):
      1. Requestor cannot be first signer (no self-approval).
      2. Second signer must be a DIFFERENT officer than the first signer.
      3. Status must match the expected stage for the signature.
      4. Every state change is logged to disbursement_audit.
    """
    d = db.query(Disbursement).filter(Disbursement.id == disbursement_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Disbursement not found")

    signer = user["user_id"]
    now = datetime.now(timezone.utc)
    prev_status = d.status

    if body.signature_role == "first":
        # Must be in pending_first_sig state
        if d.status != "pending_first_sig":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot apply first signature: disbursement is in '{d.status}' state.",
            )

        # RULE 1: Requestor cannot self-approve
        if signer == d.requested_by:
            raise HTTPException(
                status_code=403,
                detail="Self-approval is not permitted. The requestor cannot sign their own disbursement.",
            )

        if not body.approved:
            # First signer rejecting
            d.status = "rejected"
            _write_audit(db, d.id, "reject_first", signer, prev_status, "rejected",
                         notes="Rejected at first signature stage")
        else:
            d.first_signature_by = signer
            d.first_signature_at = now
            d.status = "pending_second_sig"
            _write_audit(db, d.id, "sign_first", signer, prev_status, "pending_second_sig")

    elif body.signature_role == "second":
        # Must be in pending_second_sig state
        if d.status != "pending_second_sig":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot apply second signature: disbursement is in '{d.status}' state.",
            )

        # RULE 2: Second signer must be different from first signer
        if signer == d.first_signature_by:
            raise HTTPException(
                status_code=403,
                detail="Second signature must be from a different officer than the first signer.",
            )

        if not body.approved:
            # Second signer rejecting
            d.status = "rejected"
            _write_audit(db, d.id, "reject_second", signer, prev_status, "rejected",
                         notes="Rejected at second signature stage")
        else:
            d.second_signature_by = signer
            d.second_signature_at = now
            d.status = "approved"
            d.approved_at = now
            _write_audit(db, d.id, "sign_second_approve", signer, prev_status, "approved")

    else:
        raise HTTPException(status_code=422, detail="signature_role must be 'first' or 'second'")

    db.commit()
    db.refresh(d)
    return _disbursement_out(d)


# ---------------------------------------------------------------------------
# GET /api/v1/finance/dues-remittances
# ---------------------------------------------------------------------------


@router.get("/dues-remittances", response_model=list[DuesRemittanceOut])
async def list_dues_remittances(
    facility: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DuesRemittanceOut]:
    q = db.query(DuesRemittance)
    if facility:
        q = q.filter(DuesRemittance.facility == facility)
    if period:
        q = q.filter(DuesRemittance.period == period)
    return [_dues_out(r) for r in q.order_by(DuesRemittance.period.desc()).all()]


# ---------------------------------------------------------------------------
# POST /api/v1/finance/dues-remittances
# ---------------------------------------------------------------------------


@router.post("/dues-remittances", response_model=DuesRemittanceOut, status_code=201)
async def create_dues_remittance(
    body: DuesRemittanceCreate,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DuesRemittanceOut:
    received_dt: datetime | None = None
    if body.received_date:
        try:
            received_dt = datetime.fromisoformat(body.received_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid received_date: {exc}") from exc

    r = DuesRemittance(
        facility=body.facility,
        period=body.period,
        expected_amount=body.expected_amount,
        received_amount=body.received_amount,
        received_date=received_dt,
        reconciled=False,
        notes=body.notes,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _dues_out(r)


# ---------------------------------------------------------------------------
# GET /api/v1/finance/dues-remittances/arrears
# ---------------------------------------------------------------------------


@router.get("/dues-remittances/arrears")
async def dues_arrears(
    period: Optional[str] = Query(None, description="YYYY-MM — defaults to current month"),
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return facilities with missing or partial remittances for the given period."""
    target_period = period or _CURRENT_PERIOD
    remittances = (
        db.query(DuesRemittance)
        .filter(DuesRemittance.period == target_period)
        .all()
    )
    in_arrears = [
        {
            "facility": r.facility,
            "period": r.period,
            "expected_amount": r.expected_amount,
            "received_amount": r.received_amount,
            "shortfall": round(r.expected_amount - r.received_amount, 2),
        }
        for r in remittances
        if r.received_amount < r.expected_amount and not r.reconciled
    ]
    return {
        "period": target_period,
        "arrears_count": len(in_arrears),
        "facilities": in_arrears,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/finance/audit
# ---------------------------------------------------------------------------


@router.get("/audit", response_model=list[AuditEntryOut])
async def get_audit_log(
    disbursement_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditEntryOut]:
    """Return disbursement audit trail.

    - With disbursement_id: returns that disbursement's full audit history
      (any authenticated user).
    - Without disbursement_id: returns the full audit log, paginated
      (OFFICER role only).
    """
    q = db.query(DisbursementAudit)

    if disbursement_id is not None:
        q = q.filter(DisbursementAudit.disbursement_id == disbursement_id)
    else:
        # Full log — officer only
        from integrations.pulse.core.roles import _has_officer_role
        if not _has_officer_role(user):
            raise HTTPException(
                status_code=403,
                detail="Officer role required to view the full audit log.",
            )
        # order_by MUST come before offset/limit
        q = q.order_by(DisbursementAudit.performed_at.asc()).offset(offset).limit(limit)
        return [_audit_out(a) for a in q.all()]

    return [_audit_out(a) for a in q.order_by(DisbursementAudit.performed_at.asc()).all()]


# ---------------------------------------------------------------------------
# Context bundle helper — used by agents context endpoint
# ---------------------------------------------------------------------------


def build_finance_context(db: Session) -> dict[str, Any]:
    """Build the 'finance' section for SecTreas agent context bundle."""
    all_disbursements = db.query(Disbursement).all()

    pending_cosig = sum(
        1 for d in all_disbursements
        if d.status in ("pending_first_sig", "pending_second_sig")
    )

    approved = [d for d in all_disbursements if d.status == "approved"]
    ytd = sum(d.amount for d in approved)

    # Dues arrears for current period
    current_remittances = (
        db.query(DuesRemittance)
        .filter(DuesRemittance.period == _CURRENT_PERIOD)
        .all()
    )
    arrears_facilities = [
        r.facility
        for r in current_remittances
        if r.received_amount < r.expected_amount and not r.reconciled
    ]

    # Budget variance alert
    budget_lines = (
        db.query(BudgetLine)
        .filter(BudgetLine.fiscal_year == _CURRENT_FISCAL_YEAR)
        .all()
    )
    budget_variance_alert = any(
        bl.actual_amount > bl.budgeted_amount for bl in budget_lines
    )

    return {
        "pending_cosignature_count": pending_cosig,
        "dues_arrears_facilities": arrears_facilities,
        "ytd_disbursements": round(ytd, 2),
        "budget_variance_alert": budget_variance_alert,
    }
