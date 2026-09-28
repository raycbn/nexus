"""add teams memberships invitations

Revision ID: fc2e3f4a5b67
Revises: fb1d2e3f4a56
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fc2e3f4a5b67"
down_revision: str | None = "fb1d2e3f4a56"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "teams",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "organization_id",
            uuid,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_teams_org_name", "teams", ["organization_id", "name"])
    op.create_index("ix_teams_org", "teams", ["organization_id"])
    op.create_table(
        "memberships",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "organization_id",
            uuid,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_memberships_org_user", "memberships", ["organization_id", "user_id"]
    )
    op.create_index("ix_memberships_org", "memberships", ["organization_id"])
    op.create_table(
        "team_memberships",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "organization_id",
            uuid,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_id", uuid, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_team_memberships_team_user", "team_memberships", ["team_id", "user_id"]
    )
    op.create_index("ix_team_memberships_team", "team_memberships", ["team_id"])
    op.create_table(
        "invitations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "organization_id",
            uuid,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("invitations")
    op.drop_index("ix_team_memberships_team", table_name="team_memberships")
    op.drop_constraint("uq_team_memberships_team_user", "team_memberships", type_="unique")
    op.drop_table("team_memberships")
    op.drop_index("ix_memberships_org", table_name="memberships")
    op.drop_constraint("uq_memberships_org_user", "memberships", type_="unique")
    op.drop_table("memberships")
    op.drop_index("ix_teams_org", table_name="teams")
    op.drop_constraint("uq_teams_org_name", "teams", type_="unique")
    op.drop_table("teams")
