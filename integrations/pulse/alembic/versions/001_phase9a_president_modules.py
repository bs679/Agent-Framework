"""Phase 9a — President officer modules: grievances, legislative, board tables.

Revision ID: 001_phase9a
Revises: (none — first migration)
Create Date: 2026-02-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "001_phase9a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # MODULE 1 — Grievance Intelligence
    # ------------------------------------------------------------------
    op.create_table(
        "grievances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_number", sa.String(50), nullable=False),
        sa.Column(
            "facility",
            sa.String(30),
            nullable=False,
            comment="Bradley | Norwalk | Waterbury | Region12 | Region13 | Region17",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="open",
            comment="open | pending_arbitration | closed | withdrawn",
        ),
        sa.Column(
            "type",
            sa.String(40),
            nullable=False,
            comment="discipline | contract_violation | working_conditions | other",
        ),
        sa.Column("filed_date", sa.Date(), nullable=False),
        sa.Column("step1_deadline", sa.Date(), nullable=False),
        sa.Column("step2_deadline", sa.Date(), nullable=False),
        sa.Column("arbitration_deadline", sa.Date(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number"),
    )
    op.create_index("ix_grievances_id", "grievances", ["id"])
    op.create_index("ix_grievances_case_number", "grievances", ["case_number"])

    op.create_table(
        "grievance_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grievance_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.ForeignKeyConstraint(["grievance_id"], ["grievances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grievance_events_id", "grievance_events", ["id"])
    op.create_index("ix_grievance_events_grievance_id", "grievance_events", ["grievance_id"])

    op.create_table(
        "grievance_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grievance_id", sa.Integer(), nullable=False),
        sa.Column(
            "deadline_type",
            sa.String(20),
            nullable=False,
            comment="step1 | step2 | arbitration",
        ),
        sa.Column("days_remaining", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["grievance_id"], ["grievances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grievance_alerts_id", "grievance_alerts", ["id"])
    op.create_index("ix_grievance_alerts_grievance_id", "grievance_alerts", ["grievance_id"])

    # ------------------------------------------------------------------
    # MODULE 3 — Legislative Intelligence
    # ------------------------------------------------------------------
    op.create_table(
        "legislative_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_number", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("committee", sa.String(150), nullable=True),
        sa.Column("hearing_date", sa.Date(), nullable=True),
        sa.Column(
            "relevance",
            sa.String(10),
            nullable=False,
            server_default="medium",
            comment="high | medium | low",
        ),
        sa.Column("status", sa.String(60), nullable=False, server_default="active"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legislative_items_id", "legislative_items", ["id"])
    op.create_index("ix_legislative_items_bill_number", "legislative_items", ["bill_number"])
    op.create_index("ix_legislative_items_hearing_date", "legislative_items", ["hearing_date"])

    # ------------------------------------------------------------------
    # MODULE 4 — Executive Board Support
    # ------------------------------------------------------------------
    op.create_table(
        "board_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column(
            "type",
            sa.String(30),
            nullable=False,
            server_default="regular",
            comment="regular | special | executive_session",
        ),
        sa.Column("quorum_met", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_meetings_id", "board_meetings", ["id"])
    op.create_index("ix_board_meetings_date", "board_meetings", ["date"])

    op.create_table(
        "bylaw_compliance_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requirement", sa.String(300), nullable=False),
        sa.Column("frequency", sa.String(30), nullable=False),
        sa.Column("last_completed", sa.Date(), nullable=True),
        sa.Column("next_due", sa.Date(), nullable=False),
        sa.Column("assigned_to", sa.String(120), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="pending | completed | overdue",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bylaw_compliance_items_id", "bylaw_compliance_items", ["id"])
    op.create_index("ix_bylaw_compliance_items_next_due", "bylaw_compliance_items", ["next_due"])


def downgrade() -> None:
    op.drop_table("bylaw_compliance_items")
    op.drop_table("board_meetings")
    op.drop_table("legislative_items")
    op.drop_table("grievance_alerts")
    op.drop_table("grievance_events")
    op.drop_table("grievances")
