"""add investigation phase

Revision ID: 7b8c9d0e1f23
Revises: f1a2b3c4d567
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b8c9d0e1f23"
down_revision: str | None = "f1a2b3c4d567"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigations",
        sa.Column("phase", sa.String(length=32), nullable=False, server_default="collection"),
    )
    op.alter_column("investigations", "phase", server_default=None)


def downgrade() -> None:
    op.drop_column("investigations", "phase")
