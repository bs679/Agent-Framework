"""SQLAlchemy ORM models for Pulse.

Tables
------
- check_ins       : Daily agent check-in records
- captures        : Quick-capture notes from Pulse UI
- agent_registry  : Agent metadata (mirrors agents/ directory on disk)

pgvector columns are used on text-heavy fields for semantic search.
Install pgvector extension before running migrations:
    CREATE EXTENSION IF NOT EXISTS vector;
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import]
    _VECTOR_AVAILABLE = True
except ImportError:
    # pgvector not installed — vector columns will be unavailable.
    # Migrations will fail if pgvector is missing; install it first.
    Vector = None  # type: ignore[assignment,misc]
    _VECTOR_AVAILABLE = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CheckIn(Base):
    """Daily agent check-in record (morning / evening)."""

    __tablename__ = "check_ins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    checkin_id: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    checkin_type: Mapped[str] = mapped_column(String(16), nullable=False)  # morning|evening
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_check_ins_owner_stored", "owner_id", "stored_at"),
    )


class Capture(Base):
    """Quick-capture note submitted via the Pulse UI."""

    __tablename__ = "captures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(String(32), nullable=True)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # pgvector embedding for semantic search on capture content.
    # Populated asynchronously after capture is saved.
    if _VECTOR_AVAILABLE:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(1536), nullable=True
        )


class AgentRegistry(Base):
    """Registry of provisioned agents (mirrors agents/ directory)."""

    __tablename__ = "agent_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plane_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_checkin_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    container_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown"
    )  # running | stopped | unknown
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
