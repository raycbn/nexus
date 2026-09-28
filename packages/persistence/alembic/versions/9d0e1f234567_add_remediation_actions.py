"""add remediation actions

Revision ID: 9d0e1f234567
Revises: 8c9d0e1f2345
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9d0e1f234567"
down_revision = "8c9d0e1f2345"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remediation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_key", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("command_preview", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remediation_actions_organization_id",
        "remediation_actions",
        ["organization_id"],
    )
    op.create_index(
        "ix_remediation_actions_investigation_id",
        "remediation_actions",
        ["investigation_id"],
    )
    op.create_index(
        "ix_remediation_actions_resource_id",
        "remediation_actions",
        ["resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_actions_resource_id", table_name="remediation_actions")
    op.drop_index("ix_remediation_actions_investigation_id", table_name="remediation_actions")
    op.drop_index("ix_remediation_actions_organization_id", table_name="remediation_actions")
    op.drop_table("remediation_actions")
