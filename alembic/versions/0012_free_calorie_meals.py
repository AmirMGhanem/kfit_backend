"""free-calorie catalog items (mealtype 'free' + 4 rows)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-08

Represents the free-calorie allowance (R1) as real catalog items so it becomes a
concrete plan line. Adds 'free' to the mealtype enum (via rename-recreate, since
the env runs the whole upgrade in one transaction and ADD VALUE can't be used in
the same tx) and seeds the four buckets 120/150/200/250.

The value is still chosen in code (10% of daily -> nearest bucket); the agent
never selects these — code attaches the matching row as the plan's free item.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FREE_BUCKETS = (120, 150, 200, 250)
FREE_NAME = "קלוריות חופשיות"


def upgrade() -> None:
    # ── Recreate the enum with 'free' (transaction-safe) ────────────────────
    op.execute("ALTER TABLE meals ALTER COLUMN meal_type DROP DEFAULT")
    op.execute("ALTER TYPE mealtype RENAME TO mealtype_old")
    op.execute("CREATE TYPE mealtype AS ENUM ('generic', 'snack', 'free')")
    op.execute(
        "ALTER TABLE meals ALTER COLUMN meal_type TYPE mealtype "
        "USING meal_type::text::mealtype"
    )
    op.execute(
        "ALTER TABLE meal_plan_items ALTER COLUMN meal_type TYPE mealtype "
        "USING meal_type::text::mealtype"
    )
    op.execute("ALTER TABLE meals ALTER COLUMN meal_type SET DEFAULT 'generic'")
    op.execute("DROP TYPE mealtype_old")

    # ── Seed the four free-calorie buckets ──────────────────────────────────
    stmt = sa.text(
        "INSERT INTO meals (name, calories, meal_type, payload, is_active, "
        "has_fat_source, suitable_as_big_meal) "
        "VALUES (:name, :cal, 'free', '{\"_seed\": \"free-calories-v1\"}'::jsonb, "
        "true, false, false)"
    )
    bind = op.get_bind()
    for cal in FREE_BUCKETS:
        bind.execute(stmt, {"name": FREE_NAME, "cal": cal})


def downgrade() -> None:
    # Remove free plan items + free catalog rows before dropping the value.
    op.execute(
        "DELETE FROM meal_plan_items WHERE meal_id IN "
        "(SELECT id FROM meals WHERE meal_type = 'free')"
    )
    op.execute("DELETE FROM meals WHERE meal_type = 'free'")

    op.execute("ALTER TABLE meals ALTER COLUMN meal_type DROP DEFAULT")
    op.execute("ALTER TYPE mealtype RENAME TO mealtype_old")
    op.execute("CREATE TYPE mealtype AS ENUM ('generic', 'snack')")
    op.execute(
        "ALTER TABLE meals ALTER COLUMN meal_type TYPE mealtype "
        "USING meal_type::text::mealtype"
    )
    op.execute(
        "ALTER TABLE meal_plan_items ALTER COLUMN meal_type TYPE mealtype "
        "USING meal_type::text::mealtype"
    )
    op.execute("ALTER TABLE meals ALTER COLUMN meal_type SET DEFAULT 'generic'")
    op.execute("DROP TYPE mealtype_old")
