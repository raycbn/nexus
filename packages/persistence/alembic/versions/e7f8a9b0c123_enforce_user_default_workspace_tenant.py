"""Enforce user default workspace tenant consistency.

Revision ID: e7f8a9b0c123
Revises: d5e6f7a8b901
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c123"
down_revision: str | None = "d5e6f7a8b901"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    invalid_users = bind.execute(
        sa.text(
            "SELECT count(*) FROM users u "
            "JOIN workspaces w ON w.id = u.default_workspace_id "
            "WHERE u.default_workspace_id IS NOT NULL "
            "AND u.organization_id <> w.organization_id"
        )
    ).scalar_one()

    if invalid_users:
        raise RuntimeError(
            "Cannot enforce user default workspace tenant consistency: "
            f"{invalid_users} invalid users."
        )

    op.create_foreign_key(
        "fk_users_default_workspace_organization",
        "users",
        "workspaces",
        ["default_workspace_id", "organization_id"],
        ["id", "organization_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_default_workspace_organization",
        "users",
        type_="foreignkey",
    )
