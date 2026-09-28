"""add remediation audit event values

Revision ID: 9e1f23456789
Revises: 9d0e1f234567
"""

from alembic import op

revision = "9e1f23456789"
down_revision = "9d0e1f234567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'remediation_proposed'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'remediation_approved'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'remediation_rejected'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely in-place.
    pass
