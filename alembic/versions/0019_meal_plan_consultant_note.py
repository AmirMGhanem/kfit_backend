"""meal_plans.consultant_note — the consultant's free-text steer

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-26

Nullable text holding what the consultant asked for when (re)generating a
plan ("big meal lighter, no fish"). NULL for plans generated without a note.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meal_plans", sa.Column("consultant_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_plans", "consultant_note")
