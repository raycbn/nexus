"""add encrypted vault fields to credentials

Revision ID: fb1d2e3f4a56
Revises: fa0c1d2e3f45
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "fb1d2e3f4a56"
down_revision: str | None = "fa0c1d2e3f45"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("credentials", sa.Column("ciphertext_blob", sa.LargeBinary(), nullable=True))
    op.add_column("credentials", sa.Column("nonce_blob", sa.LargeBinary(), nullable=True))
    op.add_column("credentials", sa.Column("key_version", sa.Integer(), nullable=True))
    op.add_column(
        "credentials",
        sa.Column("status", sa.String(32), nullable=False, server_default="external"),
    )
    op.add_column("credentials", sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("credentials", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("credentials", "revoked_at")
    op.drop_column("credentials", "rotated_at")
    op.drop_column("credentials", "status")
    op.drop_column("credentials", "key_version")
    op.drop_column("credentials", "nonce_blob")
    op.drop_column("credentials", "ciphertext_blob")
