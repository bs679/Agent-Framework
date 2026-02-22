"""Initial schema: pgvector extension + check_ins, captures, agent_registry

Revision ID: 0001
Revises:
Create Date: 2026-02-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (requires PostgreSQL 12+ and pgvector installed)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── check_ins ────────────────────────────────────────────────────────────
    op.create_table(
        "check_ins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("checkin_id", sa.String(24), nullable=False, unique=True),
        sa.Column("checkin_type", sa.String(16), nullable=False),
        sa.Column(
            "stored_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_check_ins_owner_id", "check_ins", ["owner_id"])
    op.create_index(
        "ix_check_ins_owner_stored", "check_ins", ["owner_id", "stored_at"]
    )

    # ── captures ─────────────────────────────────────────────────────────────
    op.create_table(
        "captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("suggested_action", sa.String(32), nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed", sa.Boolean, nullable=False, server_default="false"),
        # pgvector embedding (1536-dim, OpenAI-compatible; adjust for local model)
        sa.Column(
            "embedding",
            sa.Text,  # placeholder — replaced by vector type via raw SQL below
            nullable=True,
        ),
    )
    # Replace placeholder Text column with actual vector type
    op.execute("ALTER TABLE captures ALTER COLUMN embedding TYPE vector(1536) USING NULL")
    op.create_index("ix_captures_owner_id", "captures", ["owner_id"])
    # IVFFlat index for approximate nearest-neighbour search on embeddings
    op.execute(
        "CREATE INDEX ix_captures_embedding_ivfflat "
        "ON captures USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # ── agent_registry ────────────────────────────────────────────────────────
    op.create_table(
        "agent_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False, unique=True),
        sa.Column("owner_email", sa.String(255), nullable=False),
        sa.Column("plane_name", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="standard"),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "container_status", sa.String(16), nullable=False, server_default="unknown"
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_agent_registry_owner_email", "agent_registry", ["owner_email"])


def downgrade() -> None:
    op.drop_table("agent_registry")
    op.drop_table("captures")
    op.drop_table("check_ins")
    op.execute("DROP EXTENSION IF EXISTS vector")
