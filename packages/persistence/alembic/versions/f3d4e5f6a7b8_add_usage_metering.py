"""add usage metering"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3d4e5f6a7b8"
down_revision: str | None = "f2c3d4e5f6a7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_usage_events_org_metric", "usage_events", ["organization_id", "metric"]
    )
    op.create_index(
        "ix_usage_events_org_occurred", "usage_events", ["organization_id", "occurred_at"]
    )
    op.create_index(
        "ix_usage_events_workspace_metric", "usage_events", ["workspace_id", "metric"]
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_workspace_metric", table_name="usage_events")
    op.drop_index("ix_usage_events_org_occurred", table_name="usage_events")
    op.drop_index("ix_usage_events_org_metric", table_name="usage_events")
    op.drop_table("usage_events")

