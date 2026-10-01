"""add AI provider settings

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_provider", sa.String(64), nullable=False),
        sa.Column("primary_model", sa.String(255), nullable=False),
        sa.Column("primary_credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_base_url", sa.String(512), nullable=True),
        sa.Column("fallback_provider", sa.String(64), nullable=True),
        sa.Column("fallback_model", sa.String(255), nullable=True),
        sa.Column("fallback_credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fallback_base_url", sa.String(512), nullable=True),
        sa.Column("local_model", sa.String(255), nullable=False),
        sa.Column("task_policies", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_settings_organization_id", "ai_settings", ["organization_id"])
    op.create_index("ix_ai_settings_workspace_id", "ai_settings", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_settings_workspace_id", table_name="ai_settings")
    op.drop_index("ix_ai_settings_organization_id", table_name="ai_settings")
    op.drop_table("ai_settings")
