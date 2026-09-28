"""add discovery run history"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a9b0c1d234"
down_revision: str | None = "f7d9e1a2b456"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_discovery_runs_org",
        "discovery_runs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_discovery_runs_resource",
        "discovery_runs",
        "resources",
        ["resource_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_discovery_runs_organization_id", "discovery_runs", ["organization_id"])
    op.create_index("ix_discovery_runs_workspace_id", "discovery_runs", ["workspace_id"])
    op.create_index("ix_discovery_runs_resource_id", "discovery_runs", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_discovery_runs_resource_id", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_workspace_id", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_organization_id", table_name="discovery_runs")
    op.drop_table("discovery_runs")
