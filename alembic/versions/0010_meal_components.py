"""meal full component detail + fat-source flags

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-07

Adds the full component breakdown from kfit_meal_full_components_table.xlsx:
meal structure, veg/fat group calories, fat source text, notes, and the two
flags that drive the fat rule — has_fat_source and suitable_as_big_meal.

Backfill is keyed by ``calories`` (unique across the 41 seed meals) so it applies
identically in every environment.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMPONENTS = json.loads(
    r"""
[
  {
    "calories": 340,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 400,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 450,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 410,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 470,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 520,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 570,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 630,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 480,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 540,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 590,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 640,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 700,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 770,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 860,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 840,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 930,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 1000,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 1090,
    "meal_structure": "חלבון + פחמימה + ירקות",
    "veg_group_calories": 60,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אין מקור שומן מובנה; לא לבחור כארוחה הגדולה אם נדרש שומן."
  },
  {
    "calories": 385,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 445,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 495,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 455,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 515,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 565,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 615,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 675,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 525,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 585,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 635,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 685,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 745,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 815,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 905,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 885,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 975,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 1045,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 1135,
    "meal_structure": "חלבון + פחמימה + ירקות + שומן בריא",
    "veg_group_calories": 60,
    "fat_group_calories": 45,
    "fat_source": "כפית שמן זית / כפית טחינה",
    "has_fat_source": true,
    "suitable_as_big_meal": true,
    "notes": "מתאימה כארוחה גדולה כי יש בה מקור שומן מובנה."
  },
  {
    "calories": 100,
    "meal_structure": "פחמימה בלבד",
    "veg_group_calories": 0,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "מתאים כסנאק פחמימה; אם הלקוח רוצה פירות אפשר לבחור פרי מתוך קבוצת הפחמימה."
  },
  {
    "calories": 140,
    "meal_structure": "חלבון בלבד",
    "veg_group_calories": 0,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "מתאים כסנאק חלבון; לא להחשיב חטיף אנרגיה כחלבון."
  },
  {
    "calories": 240,
    "meal_structure": "חלבון + פחמימה",
    "veg_group_calories": 0,
    "fat_group_calories": 0,
    "fat_source": null,
    "has_fat_source": false,
    "suitable_as_big_meal": false,
    "notes": "אם מוסיפים סנאק, הקלוריות יורדות מהארוחה הגדולה."
  }
]
"""
)


def upgrade() -> None:
    op.add_column("meals", sa.Column("meal_structure", sa.String(), nullable=True))
    op.add_column("meals", sa.Column("veg_group_calories", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("fat_group_calories", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("fat_source", sa.String(), nullable=True))
    op.add_column("meals", sa.Column("notes", sa.String(), nullable=True))
    op.add_column(
        "meals",
        sa.Column(
            "has_fat_source",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "meals",
        sa.Column(
            "suitable_as_big_meal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    stmt = sa.text(
        "UPDATE meals SET "
        "meal_structure = :meal_structure, "
        "veg_group_calories = :veg_group_calories, "
        "fat_group_calories = :fat_group_calories, "
        "fat_source = :fat_source, "
        "notes = :notes, "
        "has_fat_source = :has_fat_source, "
        "suitable_as_big_meal = :suitable_as_big_meal "
        "WHERE calories = :calories"
    )
    bind = op.get_bind()
    for c in COMPONENTS:
        bind.execute(stmt, c)


def downgrade() -> None:
    for col in (
        "suitable_as_big_meal",
        "has_fat_source",
        "notes",
        "fat_source",
        "fat_group_calories",
        "veg_group_calories",
        "meal_structure",
    ):
        op.drop_column("meals", col)
