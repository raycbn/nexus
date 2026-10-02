"""merge all current Alembic heads into a single lineage

Revision ID: fff001122334
Revises: e5f6a7b8c9d0, f5b7c9d1e234, f6a7b8c9d0e1, fe4f5a6b7c89
"""

revision = "fff001122334"
down_revision = (
    "e5f6a7b8c9d0",
    "f5b7c9d1e234",
    "f6a7b8c9d0e1",
    "fe4f5a6b7c89",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
