"""add billing plans and subscriptions"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4d5e6f7a8b9"
down_revision = "f3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="eur"),
        sa.Column("included_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stripe_price_id", sa.String(255)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    plans = sa.table(
        "billing_plans",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("monthly_price_cents", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("included_units", sa.Integer),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(
        plans,
        [
            {
                "id": "10000000-0000-0000-0000-000000000001",
                "key": "free",
                "name": "Free",
                "description": "For evaluation and personal labs",
                "monthly_price_cents": 0,
                "currency": "eur",
                "included_units": 10000,
                "enabled": True,
            },
            {
                "id": "10000000-0000-0000-0000-000000000002",
                "key": "pro",
                "name": "Pro",
                "description": "For growing operations teams",
                "monthly_price_cents": 4900,
                "currency": "eur",
                "included_units": 1000000,
                "enabled": True,
            },
            {
                "id": "10000000-0000-0000-0000-000000000003",
                "key": "enterprise",
                "name": "Enterprise",
                "description": "Advanced enterprise operations",
                "monthly_price_cents": 0,
                "currency": "eur",
                "included_units": 0,
                "enabled": True,
            },
        ],
    )
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("billing_plans.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255), unique=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("billing_subscriptions")
    op.drop_table("billing_plans")
