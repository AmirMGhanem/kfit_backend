"""meal_plans.free_calories

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-07

The free-calorie budget (R1). Under the nutrition rules the meals sum to
(daily − free_calories), so this is stored to interpret the plan correctly.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meal_plans", sa.Column("free_calories", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_plans", "free_calories")
