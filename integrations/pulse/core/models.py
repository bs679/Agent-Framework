"""SQLAlchemy ORM models for Pulse.

Tables
------
user_profiles     — maps Azure AD user IDs to roles and role_detail
compliance_items  — recurring compliance obligations for CHCA
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from integrations.pulse.core.database import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    """Top-level role assigned to each Pulse user."""

    ADMIN = "ADMIN"      # President (Dave) — full capabilities
    OFFICER = "OFFICER"  # SecTreas / ExecSec — officer-level capabilities
    STAFF = "STAFF"      # Remaining 5 staff — standard context only


class RoleDetail(str, enum.Enum):
    """Sub-role for officers, distinguishing SecTreas from ExecSec."""

    president = "president"
    sectreasurer = "sectreasurer"
    execsecretary = "execsecretary"
    staff = "staff"


class ComplianceCategory(str, enum.Enum):
    financial = "financial"
    legal = "legal"
    bylaw = "bylaw"
    reporting = "reporting"
    other = "other"


class ComplianceFrequency(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"
    one_time = "one_time"


class AssignedToRole(str, enum.Enum):
    """Which role(s) are responsible for / can see this obligation."""

    ADMIN = "ADMIN"
    OFFICER = "OFFICER"
    STAFF = "STAFF"
    ALL = "ALL"


class ComplianceStatus(str, enum.Enum):
    upcoming = "upcoming"
    due_soon = "due_soon"
    overdue = "overdue"
    completed = "completed"


# ---------------------------------------------------------------------------
# user_profiles
# ---------------------------------------------------------------------------

class UserProfile(Base):
    """Maps an Azure AD user to their Pulse role and sub-role.

    A profile is created automatically on first login (STAFF by default)
    and can be updated via POST /api/v1/admin/users/{user_id}/role-detail
    (ADMIN only).
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    azure_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.STAFF.value,
    )
    role_detail: Mapped[str] = mapped_column(
        Enum(RoleDetail, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RoleDetail.staff.value,
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<UserProfile id={self.id} user={self.azure_user_id!r} "
            f"role={self.role} role_detail={self.role_detail}>"
        )


# ---------------------------------------------------------------------------
# compliance_items
# ---------------------------------------------------------------------------

class ComplianceItem(Base):
    """A recurring compliance obligation that CHCA must meet.

    All 8 agents share visibility into these items, filtered by their role.
    """

    __tablename__ = "compliance_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        Enum(ComplianceCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplianceCategory.other.value,
    )
    frequency: Mapped[str] = mapped_column(
        Enum(ComplianceFrequency, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplianceFrequency.annual.value,
    )
    last_completed: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    assigned_to_role: Mapped[str] = mapped_column(
        Enum(AssignedToRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AssignedToRole.ALL.value,
    )
    status: Mapped[str] = mapped_column(
        Enum(ComplianceStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplianceStatus.upcoming.value,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def days_until_due(self) -> Optional[int]:
        """Return number of days until next_due (negative if overdue)."""
        if self.next_due is None:
            return None
        return (self.next_due - date.today()).days

    def refresh_status(self) -> None:
        """Recalculate status based on next_due date."""
        days = self.days_until_due()
        if days is None:
            return
        if days < 0:
            self.status = ComplianceStatus.overdue.value
        elif days <= 30:
            self.status = ComplianceStatus.due_soon.value
        else:
            self.status = ComplianceStatus.upcoming.value

    def __repr__(self) -> str:
        return (
            f"<ComplianceItem id={self.id} title={self.title!r} "
            f"next_due={self.next_due} assigned_to={self.assigned_to_role}>"
        )
