"""SQLAlchemy models for Module 4 — Executive Board Support.

Tables:
  board_meetings          — Meeting records (date, type, quorum)
  bylaw_compliance_items  — Recurring bylaw obligations and their due dates
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from integrations.pulse.db.session import Base


class BoardMeeting(Base):
    """Record of an Executive Board meeting."""

    __tablename__ = "board_meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Meeting type
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="regular",
        comment="regular | special | executive_session",
    )

    # Quorum is nullable — may not be recorded until after the meeting
    quorum_met: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class BylawComplianceItem(Base):
    """A recurring bylaw obligation that must be completed on a schedule.

    Examples: annual audit review, officer elections, financial report to membership.
    The ``next_due`` field is the authoritative deadline surfaced in the compliance
    calendar and the board context bundle.
    """

    __tablename__ = "bylaw_compliance_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requirement: Mapped[str] = mapped_column(String(300), nullable=False)

    # Human-readable schedule description (e.g., "monthly", "quarterly", "annual")
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)

    last_completed: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_due: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending | completed | overdue",
    )
