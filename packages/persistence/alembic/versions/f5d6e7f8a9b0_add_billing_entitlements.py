"""add billing entitlements"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5d6e7f8a9b0"
down_revision = "f4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("billing_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_key", sa.String(128), nullable=False),
        sa.Column("limit_value", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("plan_id", "feature_key"),
    )
    entitlements = sa.table(
        "billing_entitlements",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("plan_id", postgresql.UUID(as_uuid=True)),
        sa.column("feature_key", sa.String),
        sa.column("limit_value", sa.Integer),
    )
    rows = [
        ("10000000-0000-0000-0000-000000000001", "resources.max", 10),
        ("10000000-0000-0000-0000-000000000001", "usage.units", 10000),
        ("10000000-0000-0000-0000-000000000002", "resources.max", 1000),
        ("10000000-0000-0000-0000-000000000002", "usage.units", 1000000),
        ("10000000-0000-0000-0000-000000000003", "resources.max", None),
        ("10000000-0000-0000-0000-000000000003", "usage.units", None),
    ]
    values = []
    for i, (plan_id, feature_key, limit_value) in enumerate(rows, 1):
        values.append({"id": f"10000000-0000-0000-0000-{i:012d}", "plan_id": plan_id,
                       "feature_key": feature_key, "limit_value": limit_value})
    op.bulk_insert(entitlements, values)


def downgrade() -> None:
    op.drop_table("billing_entitlements")
