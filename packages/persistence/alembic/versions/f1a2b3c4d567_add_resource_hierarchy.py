"""add resource hierarchy

Revision ID: f1a2b3c4d567
Revises: e7f8a9b0c123
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d567"
down_revision: str | None = "e7f8a9b0c123"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column("parent_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_resources_parent_resource",
        "resources",
        "resources",
        ["parent_resource_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_resources_parent_resource_id",
        "resources",
        ["parent_resource_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_resources_parent_resource_id", table_name="resources")
    op.drop_constraint("fk_resources_parent_resource", "resources", type_="foreignkey")
    op.drop_column("resources", "parent_resource_id")
