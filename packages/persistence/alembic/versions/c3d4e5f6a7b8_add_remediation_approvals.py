"""add remediation approvals

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'remediation_rolled_back'")
    op.create_table(
        "remediation_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("remediation_action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["remediation_action_id"], ["remediation_actions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "remediation_action_id", "step", name="uq_remediation_approval_action_step"
        ),
    )
    op.create_index(
        "ix_remediation_approvals_action_id", "remediation_approvals", ["remediation_action_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_approvals_action_id", table_name="remediation_approvals")
    op.drop_table("remediation_approvals")
