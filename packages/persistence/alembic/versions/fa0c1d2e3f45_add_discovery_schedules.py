"""add scheduled discovery persistence

Revision ID: fa0c1d2e3f45
Revises: f9b0c1d2e345
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fa0c1d2e3f45"
down_revision: str | None = "f9b0c1d2e345"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cron_expression", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_discovery_schedules_org_workspace",
        "discovery_schedules",
        ["organization_id", "workspace_id"],
    )
    op.create_index(
        "ix_discovery_schedules_due",
        "discovery_schedules",
        ["enabled", "next_run_at"],
    )
    op.create_index(
        "ix_discovery_schedules_resource",
        "discovery_schedules",
        ["resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_schedules_resource", table_name="discovery_schedules")
    op.drop_index("ix_discovery_schedules_due", table_name="discovery_schedules")
    op.drop_index("ix_discovery_schedules_org_workspace", table_name="discovery_schedules")
    op.drop_table("discovery_schedules")
