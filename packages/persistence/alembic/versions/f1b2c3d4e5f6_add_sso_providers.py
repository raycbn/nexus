"""add organization SSO provider configuration

Revision ID: f1b2c3d4e5f6
Revises: f0a1b2c3d4e5
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sso_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("protocol", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("issuer", sa.String(1024), nullable=True),
        sa.Column("client_id", sa.String(512), nullable=True),
        sa.Column("client_secret_credential_id", sa.UUID(), nullable=True),
        sa.Column("metadata_url", sa.String(2048), nullable=True),
        sa.Column("metadata_xml", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.String(1024), nullable=True),
        sa.Column("attribute_mapping", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["client_secret_credential_id"], ["credentials.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sso_providers_organization_id", "sso_providers", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_sso_providers_organization_id", table_name="sso_providers")
    op.drop_table("sso_providers")
