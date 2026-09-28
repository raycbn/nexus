"""add resource connector bindings"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7d9e1a2b456"
down_revision: str | None = "f6c8d0e2a345"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resource_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("connector_key", sa.String(64), nullable=False),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_resource_connections_org",
        "resource_connections",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_resource_connections_resource",
        "resource_connections",
        "resources",
        ["resource_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_resource_connections_credential",
        "resource_connections",
        "credentials",
        ["credential_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_resource_connections_organization_id", "resource_connections", ["organization_id"]
    )
    op.create_index(
        "ix_resource_connections_workspace_id", "resource_connections", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_resource_connections_workspace_id", table_name="resource_connections")
    op.drop_index("ix_resource_connections_organization_id", table_name="resource_connections")
    op.drop_table("resource_connections")
