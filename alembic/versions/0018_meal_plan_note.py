"""meal_plan_note: best-effort drift explanation

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-02

Adds a nullable ``note`` column to ``meal_plans``. Set when the pipeline ships
a best-effort plan — structurally valid but outside the calorie window — with
a one-line explanation of the drift instead of failing outright.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meal_plans", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_plans", "note")
