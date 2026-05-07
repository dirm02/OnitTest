"""add lead persistence tables

Revision ID: 20260507_0001
Revises:
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260507_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("latest_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_tier", sa.String(length=50), nullable=True),
        sa.Column("matched_rule", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("lead_sessions_session_id_idx", "lead_sessions", ["session_id"], unique=True)
    op.create_index("lead_sessions_final_tier_idx", "lead_sessions", ["final_tier"], unique=False)

    op.create_table(
        "lead_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("assistant_response", sa.Text(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classification", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lead_session_id"], ["lead_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "lead_turns_lead_session_id_idx", "lead_turns", ["lead_session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("lead_turns_lead_session_id_idx", table_name="lead_turns")
    op.drop_table("lead_turns")
    op.drop_index("lead_sessions_final_tier_idx", table_name="lead_sessions")
    op.drop_index("lead_sessions_session_id_idx", table_name="lead_sessions")
    op.drop_table("lead_sessions")
