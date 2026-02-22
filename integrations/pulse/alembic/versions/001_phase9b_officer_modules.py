"""Phase 9b — Secretary/Treasurer + Executive Secretary officer module tables.

Revision ID: 001
Revises: (initial)
Create Date: 2026-02-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # board_meetings — prerequisite from Phase 9a (President module)
    # -----------------------------------------------------------------------
    op.create_table(
        "board_meetings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("meeting_date", sa.DateTime, nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="regular"),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # -----------------------------------------------------------------------
    # disbursements — co-signature workflow
    # -----------------------------------------------------------------------
    op.create_table(
        "disbursements",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("payee", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("requested_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_first_sig"),
        sa.Column("first_signature_by", sa.String(255), nullable=True),
        sa.Column("first_signature_at", sa.DateTime, nullable=True),
        sa.Column("second_signature_by", sa.String(255), nullable=True),
        sa.Column("second_signature_at", sa.DateTime, nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("check_number", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # -----------------------------------------------------------------------
    # budget_lines — fiscal year budget tracking
    # -----------------------------------------------------------------------
    op.create_table(
        "budget_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("fiscal_year", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("budgeted_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("actual_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # -----------------------------------------------------------------------
    # dues_remittances — facility dues payment records
    # -----------------------------------------------------------------------
    op.create_table(
        "dues_remittances",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("facility", sa.String(255), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("expected_amount", sa.Float, nullable=False),
        sa.Column("received_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("received_date", sa.DateTime, nullable=True),
        sa.Column("reconciled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # -----------------------------------------------------------------------
    # disbursement_audit — immutable audit trail
    # -----------------------------------------------------------------------
    op.create_table(
        "disbursement_audit",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("disbursement_id", sa.Integer, sa.ForeignKey("disbursements.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("performed_by", sa.String(255), nullable=False),
        sa.Column("performed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # -----------------------------------------------------------------------
    # meeting_minutes — minutes workflow with exec-session flag
    # -----------------------------------------------------------------------
    op.create_table(
        "meeting_minutes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("board_meeting_id", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("content_md", sa.Text, nullable=True),
        sa.Column("template_used", sa.String(100), nullable=True),
        sa.Column("executive_session_flag", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("drafted_by", sa.String(255), nullable=False),
        sa.Column("draft_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
    )

    # -----------------------------------------------------------------------
    # pulse_tasks — lightweight cross-role task notifications
    # -----------------------------------------------------------------------
    op.create_table(
        "pulse_tasks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("related_object", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pulse_tasks")
    op.drop_table("meeting_minutes")
    op.drop_table("disbursement_audit")
    op.drop_table("dues_remittances")
    op.drop_table("budget_lines")
    op.drop_table("disbursements")
    op.drop_table("board_meetings")
