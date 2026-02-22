"""SQLAlchemy models for Module 1 — Grievance Intelligence.

Tables:
  grievances          — One row per grievance case
  grievance_events    — Timeline of events on a grievance
  grievance_alerts    — Deadline alerts created by the daily monitoring job
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from integrations.pulse.db.session import Base


class Grievance(Base):
    """A union grievance case tracked across its lifecycle."""

    __tablename__ = "grievances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Facility — one of the five CHCA work sites
    facility: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Bradley | Norwalk | Waterbury | Region12 | Region13 | Region17",
    )

    # Status lifecycle
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
        comment="open | pending_arbitration | closed | withdrawn",
    )

    # Grievance category
    type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="discipline | contract_violation | working_conditions | other",
    )

    # Key dates
    filed_date: Mapped[date] = mapped_column(Date, nullable=False)
    step1_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    step2_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    arbitration_deadline: Mapped[date] = mapped_column(Date, nullable=False)

    # Outcome and freetext
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit timestamps — set automatically
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    events: Mapped[list[GrievanceEvent]] = relationship(
        "GrievanceEvent", back_populates="grievance", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[GrievanceAlert]] = relationship(
        "GrievanceAlert", back_populates="grievance", cascade="all, delete-orphan"
    )


class GrievanceEvent(Base):
    """A timestamped event in a grievance's history (step filings, responses, hearings)."""

    __tablename__ = "grievance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grievance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)

    # Relationship back to the parent grievance
    grievance: Mapped[Grievance] = relationship("Grievance", back_populates="events")


class GrievanceAlert(Base):
    """A deadline-proximity alert created by the daily monitoring job.

    Alerts are consumed by the President agent's check-in context.
    ``posted_at`` is set when the alert has been delivered to /agents/checkin.
    """

    __tablename__ = "grievance_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grievance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grievances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deadline_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="step1 | step2 | arbitration",
    )
    days_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship back to the parent grievance
    grievance: Mapped[Grievance] = relationship("Grievance", back_populates="alerts")
