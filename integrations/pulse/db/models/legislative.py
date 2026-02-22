"""SQLAlchemy model for Module 3 — Legislative Intelligence.

Table:
  legislative_items — Bills and hearings tracked for union advocacy
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from integrations.pulse.db.session import Base


class LegislativeItem(Base):
    """A CT General Assembly bill or regulatory item relevant to CHCA members."""

    __tablename__ = "legislative_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bill_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    committee: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    hearing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # Priority score assigned during intake
    relevance: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="medium",
        comment="high | medium | low",
    )
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="active")

    # Content fields — populated by n8n Workflow 3 and manual editing
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text action list; newline-separated or JSON array string",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
