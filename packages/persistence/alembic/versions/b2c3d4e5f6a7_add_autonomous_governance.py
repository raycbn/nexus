"""add autonomous governance

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "autonomous_governance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_risk_level", sa.String(16), nullable=False, server_default="medium"),
        sa.Column(
            "allow_autonomous_high_risk", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("allowed_resource_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("denied_action_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("approval_chain_user_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("maintenance_windows", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("max_affected_resources", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rollback_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "workspace_id", name="uq_autonomous_governance_scope"
        ),
    )
    op.create_index(
        "ix_autonomous_governance_org_id", "autonomous_governance", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_autonomous_governance_org_id", table_name="autonomous_governance")
    op.drop_table("autonomous_governance")
