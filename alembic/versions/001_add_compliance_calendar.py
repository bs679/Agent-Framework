"""Add user_profiles and compliance_items tables; seed compliance obligations.

Revision ID: 001
Revises:
Create Date: 2026-02-22

Phase 9c — Standard Staff Agent + Shared Compliance Calendar
"""

from __future__ import annotations

from datetime import date
from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


# ---------------------------------------------------------------------------
# Upgrade — create tables + seed data
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── user_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("azure_user_id", sa.String(255), unique=True, nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "OFFICER", "STAFF", name="userrole"),
            nullable=False,
            server_default="STAFF",
        ),
        sa.Column(
            "role_detail",
            sa.Enum(
                "president",
                "sectreasurer",
                "execsecretary",
                "staff",
                name="roledetail",
            ),
            nullable=False,
            server_default="staff",
        ),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_user_profiles_azure_user_id", "user_profiles", ["azure_user_id"])

    # ── compliance_items ───────────────────────────────────────────────────
    op.create_table(
        "compliance_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "financial", "legal", "bylaw", "reporting", "other",
                name="compliancecategory",
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "frequency",
            sa.Enum(
                "monthly", "quarterly", "annual", "one_time",
                name="compliancefrequency",
            ),
            nullable=False,
            server_default="annual",
        ),
        sa.Column("last_completed", sa.Date, nullable=True),
        sa.Column("next_due", sa.Date, nullable=True),
        sa.Column(
            "assigned_to_role",
            sa.Enum("ADMIN", "OFFICER", "STAFF", "ALL", name="assignedtorole"),
            nullable=False,
            server_default="ALL",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "upcoming", "due_soon", "overdue", "completed",
                name="compliancestatus",
            ),
            nullable=False,
            server_default="upcoming",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_compliance_items_next_due", "compliance_items", ["next_due"])

    # ── Seed data ──────────────────────────────────────────────────────────
    today = date.today()
    _seed_compliance(today)


def _next_quarter(today: date) -> date:
    for month in (1, 4, 7, 10):
        if today.month < month:
            return date(today.year, month, 1)
    return date(today.year + 1, 1, 1)


def _next_semiannual(today: date) -> date:
    if today.month < 5:
        return date(today.year, 5, 1)
    if today.month < 10:
        return date(today.year, 10, 1)
    return date(today.year + 1, 5, 1)


def _annual_due(today: date, month: int, day: int) -> date:
    candidate = date(today.year, month, day)
    if candidate <= today:
        candidate = date(today.year + 1, month, day)
    return candidate


def _next_month_first(today: date) -> date:
    from datetime import timedelta
    return (today.replace(day=1) + timedelta(days=32)).replace(day=1)


def _seed_compliance(today: date) -> None:
    compliance_table = sa.table(
        "compliance_items",
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("frequency", sa.String),
        sa.column("next_due", sa.Date),
        sa.column("assigned_to_role", sa.String),
        sa.column("status", sa.String),
        sa.column("notes", sa.Text),
    )

    items: list[dict[str, Any]] = [
        {
            "title": "Monthly dues remittance reconciliation",
            "description": (
                "Reconcile dues collected with amounts remitted to the "
                "international union. Compare payroll deduction reports "
                "against AFSCME remittance records."
            ),
            "category": "financial",
            "frequency": "monthly",
            "next_due": _next_month_first(today),
            "assigned_to_role": "OFFICER",
            "status": "upcoming",
            "notes": "Owned by Secretary-Treasurer.",
        },
        {
            "title": "Quarterly executive board meeting",
            "description": (
                "Quarterly meeting of the executive board as required by "
                "CHCA bylaws. Dave chairs; minutes drafted by ExecSec."
            ),
            "category": "bylaw",
            "frequency": "quarterly",
            "next_due": _next_quarter(today),
            "assigned_to_role": "ALL",
            "status": "upcoming",
            "notes": "All officers and executive board members must attend.",
        },
        {
            "title": "Annual LM-2 financial disclosure filing",
            "description": (
                "File the LM-2 Labor Organization Annual Report with the "
                "U.S. Department of Labor (OLMS) within 90 days of the "
                "fiscal year end."
            ),
            "category": "reporting",
            "frequency": "annual",
            "next_due": _annual_due(today, 3, 31),
            "assigned_to_role": "OFFICER",
            "status": "upcoming",
            "notes": "Secretary-Treasurer responsible. 90-day deadline after FY close.",
        },
        {
            "title": "Annual election of officers",
            "description": (
                "Conduct officer elections per Article V of the CHCA bylaws. "
                "Nominations must open at least 30 days before the election meeting."
            ),
            "category": "bylaw",
            "frequency": "annual",
            "next_due": _annual_due(today, 11, 1),
            "assigned_to_role": "ALL",
            "status": "upcoming",
            "notes": "Bylaw requirement. Coordinate with nominations committee.",
        },
        {
            "title": "Annual budget approval",
            "description": (
                "Present and vote on the annual operating budget at the "
                "executive board meeting. SecTreas prepares the draft."
            ),
            "category": "financial",
            "frequency": "annual",
            "next_due": _annual_due(today, 1, 31),
            "assigned_to_role": "ALL",
            "status": "upcoming",
            "notes": "Executive board vote required.",
        },
        {
            "title": "Annual audit",
            "description": (
                "Independent review of CHCA financial records. "
                "SecTreas coordinates with auditor and provides all "
                "supporting documentation."
            ),
            "category": "financial",
            "frequency": "annual",
            "next_due": _annual_due(today, 6, 30),
            "assigned_to_role": "OFFICER",
            "status": "upcoming",
            "notes": "Secretary-Treasurer responsible.",
        },
        {
            "title": "Monthly grievance log review",
            "description": (
                "President reviews all open grievances for deadline risks, "
                "pattern analysis, and escalation decisions."
            ),
            "category": "legal",
            "frequency": "monthly",
            "next_due": _next_month_first(today),
            "assigned_to_role": "ADMIN",
            "status": "upcoming",
            "notes": "President-only review. Feeds into monthly agent briefing.",
        },
        {
            "title": "Semi-annual member meetings",
            "description": (
                "General membership meetings held twice per year per CHCA "
                "bylaws. President presides; minutes required."
            ),
            "category": "bylaw",
            "frequency": "annual",
            "next_due": _next_semiannual(today),
            "assigned_to_role": "ALL",
            "status": "upcoming",
            "notes": "Two per year (spring + fall). Adequate notice required by bylaws.",
        },
    ]

    op.bulk_insert(compliance_table, items)


# ---------------------------------------------------------------------------
# Downgrade — drop tables (and SQLite-compatible enum cleanup)
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_table("compliance_items")
    op.drop_table("user_profiles")
