"""add investigation events

Revision ID: 8c9d0e1f2345
Revises: 7b8c9d0e1f23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8c9d0e1f2345"
down_revision = "7b8c9d0e1f23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_investigation_events_investigation_id",
        "investigation_events",
        ["investigation_id"],
    )
    op.create_index(
        "ix_investigation_events_created_at",
        "investigation_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_investigation_events_created_at", table_name="investigation_events")
    op.drop_index("ix_investigation_events_investigation_id", table_name="investigation_events")
    op.drop_table("investigation_events")
