"""add alerts"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2c3d4e5f6a7"
down_revision: str | None = "f1b2c3d4e5f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("dedup_key", sa.String(512), nullable=False),
        sa.Column("correlation_key", sa.String(512), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("incident_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_org_status", "alerts", ["organization_id", "status"])
    op.create_index("ix_alerts_org_dedup", "alerts", ["organization_id", "dedup_key"])
    op.create_index("ix_alerts_org_last_seen", "alerts", ["organization_id", "last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_org_last_seen", table_name="alerts")
    op.drop_index("ix_alerts_org_dedup", table_name="alerts")
    op.drop_index("ix_alerts_org_status", table_name="alerts")
    op.drop_table("alerts")
