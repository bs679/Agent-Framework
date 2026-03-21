"""ORM models for Secretary/Treasurer finance module.

Tables:
  - disbursements          Main disbursement workflow with co-signature enforcement
  - budget_lines           Fiscal year budget vs actual tracking
  - dues_remittances       Facility dues payment records
  - disbursement_audit     Immutable audit log of all disbursement state changes
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from integrations.pulse.db.base import Base


class Disbursement(Base):
    __tablename__ = "disbursements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payee: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Status lifecycle:
    # pending_first_sig → pending_second_sig → approved
    #                   → rejected (either stage)
    #                   → voided (post-approval admin action)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_first_sig"
    )

    first_signature_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_signature_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    second_signature_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    second_signature_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    budgeted_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DuesRemittance(Base):
    __tablename__ = "dues_remittances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2026-01"
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False)
    received_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    received_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DisbursementAudit(Base):
    """Immutable audit log — never update or delete rows from this table."""

    __tablename__ = "disbursement_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disbursement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("disbursements.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
