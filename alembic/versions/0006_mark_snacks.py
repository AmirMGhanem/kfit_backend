"""mark the meal-#2 items (20-22) as snacks

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-06

The seed (0004) types every meal as ``generic``. The three small "meal #2"
items (source item_no 20/21/22 — 100/140/240 kcal) are the catalog's snacks;
mark them so ``include_snack`` requests can be satisfied. Keyed on the stable
``payload.item_no`` because meal UUIDs differ per environment.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SNACK_ITEMS = ("20", "21", "22")


def upgrade() -> None:
    op.execute(
        "UPDATE meals SET meal_type = 'snack'::mealtype "
        "WHERE payload->>'item_no' IN ('20', '21', '22')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE meals SET meal_type = 'generic'::mealtype "
        "WHERE payload->>'item_no' IN ('20', '21', '22')"
    )
