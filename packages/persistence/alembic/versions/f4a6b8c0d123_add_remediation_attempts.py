"""add remediation execution attempts

Revision ID: f4a6b8c0d123
Revises: 9e1f23456789
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a6b8c0d123"
down_revision = "9e1f23456789"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remediation_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remediation_action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remediation_attempts_action", "remediation_attempts", ["remediation_action_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_attempts_action", table_name="remediation_attempts")
    op.drop_table("remediation_attempts")
