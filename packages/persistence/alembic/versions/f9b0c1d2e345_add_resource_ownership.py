"""add resource ownership"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9b0c1d2e345"
down_revision: str | None = "f8a9b0c1d234"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_resources_owner_user",
        "resources",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_resources_owner_user_id", "resources", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_resources_owner_user_id", table_name="resources")
    op.drop_constraint("fk_resources_owner_user", "resources", type_="foreignkey")
    op.drop_column("resources", "owner_user_id")
