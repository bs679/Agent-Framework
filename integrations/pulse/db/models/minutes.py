"""ORM models for Executive Secretary minutes workflow.

Tables:
  - meeting_minutes    Minutes lifecycle with executive-session encryption
  - pulse_tasks        Lightweight task store for cross-role notifications

The board_meetings table is owned by Phase 9a (President module) — see
``integrations.pulse.db.models.board.BoardMeeting``, re-exported here for
callers that historically imported it from this module.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from integrations.pulse.db.base import Base
from integrations.pulse.db.models.board import BoardMeeting  # noqa: F401


class MeetingMinutes(Base):
    """Minutes lifecycle for a board meeting.

    content_md stores the minutes in Markdown. When executive_session_flag
    is True, content_md is stored as Fernet-encrypted bytes (base64-encoded
    string) and only OFFICER role users may decrypt and read it.
    """

    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK to board_meetings — nullable so minutes can be created without a meeting ID
    board_meeting_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Status lifecycle: draft → pending_approval → approved → published
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft"
    )

    # content_md: plain markdown or encrypted bytes (base64) for exec sessions
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # If True, content_md is encrypted and restricted to OFFICER role
    executive_session_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    drafted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    draft_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PulseTask(Base):
    """Lightweight Pulse task — created by workflows, surfaced in agent context."""

    __tablename__ = "pulse_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    # open | completed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    # Reference to the object this task concerns (e.g. "minutes:42")
    related_object: Mapped[str | None] = mapped_column(String(100), nullable=True)
