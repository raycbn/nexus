"""add credential references

Revision ID: f6c8d0e2a345
Revises: f5b7c9d1e234
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6c8d0e2a345"
down_revision: str | None = "f5b7c9d1e234"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(64), nullable=False),
        sa.Column("secret_ref", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_credentials_organization_id", "credentials", ["organization_id"])
    op.create_index("ix_credentials_workspace_id", "credentials", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_credentials_workspace_id", table_name="credentials")
    op.drop_index("ix_credentials_organization_id", table_name="credentials")
    op.drop_table("credentials")
