"""Enforce workspace and organization consistency for resources and agents.

Revision ID: d5e6f7a8b901
Revises: c2d4e7f8a901
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b901"
down_revision: str | None = "c2d4e7f8a901"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    invalid_resources = bind.execute(
        sa.text(
            "SELECT count(*) FROM resources r "
            "JOIN workspaces w ON w.id = r.workspace_id "
            "WHERE r.workspace_id IS NOT NULL "
            "AND r.organization_id <> w.organization_id"
        )
    ).scalar_one()
    invalid_agents = bind.execute(
        sa.text(
            "SELECT count(*) FROM agents a "
            "JOIN workspaces w ON w.id = a.workspace_id "
            "WHERE a.workspace_id IS NOT NULL "
            "AND a.organization_id <> w.organization_id"
        )
    ).scalar_one()

    if invalid_resources or invalid_agents:
        raise RuntimeError(
            "Cannot enforce workspace tenant consistency: "
            f"{invalid_resources} invalid resources, {invalid_agents} invalid agents."
        )

    op.drop_constraint("fk_resources_workspace_id_workspaces", "resources", type_="foreignkey")
    op.drop_constraint("fk_agents_workspace_id_workspaces", "agents", type_="foreignkey")
    op.create_unique_constraint(
        "uq_workspaces_id_organization_id",
        "workspaces",
        ["id", "organization_id"],
    )
    op.create_foreign_key(
        "fk_resources_workspace_organization",
        "resources",
        "workspaces",
        ["workspace_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agents_workspace_organization",
        "agents",
        "workspaces",
        ["workspace_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agents_workspace_organization", "agents", type_="foreignkey")
    op.drop_constraint("fk_resources_workspace_organization", "resources", type_="foreignkey")
    op.drop_constraint(
        "uq_workspaces_id_organization_id", "workspaces", type_="unique"
    )
    op.create_foreign_key(
        "fk_agents_workspace_id_workspaces",
        "agents",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_resources_workspace_id_workspaces",
        "resources",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
