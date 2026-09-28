"""add session metadata

Revision ID: ff5a6b7c8d90
Revises: fe4f5a6b7c89
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ff5a6b7c8d90"
down_revision: str | None = "fe4f5a6b7c89"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("user_agent", sa.String(512), nullable=True))
    op.add_column("refresh_tokens", sa.Column("ip_address", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("refresh_tokens", "ip_address")
    op.drop_column("refresh_tokens", "user_agent")
