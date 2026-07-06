"""add meal nutrition detail columns and seed from CSV

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-06

Columns added to meals:
  protein_group_calories    — קבוצת חלבון (קלוריות)
  protein_group_grams       — חלבון מקבוצת החלבון (גרם)
  carb_group_calories       — קבוצת פחמימה (קלוריות)
  carb_group_protein_grams  — חלבון מקבוצת הפחמימה (גרם)
  total_protein_grams       — סה״כ חלבון בארוחה (גרם)

Seeded by matching meals.calories to kfit_meal_protein_table.csv.
The row "ארוחה" (340 kcal) has no CSV match and remains NULL.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meals", sa.Column("protein_group_calories", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("protein_group_grams", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("carb_group_calories", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("carb_group_protein_grams", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("total_protein_grams", sa.Integer(), nullable=True))

    # Seed matched by total meal calories (unique identifier across catalog).
    # Columns: calories, protein_group_cal, protein_group_g, carb_group_cal, carb_group_protein_g, total_protein_g
    op.execute("""
        UPDATE meals SET
            protein_group_calories   = v.pgc,
            protein_group_grams      = v.pgg,
            carb_group_calories      = v.cgc,
            carb_group_protein_grams = v.cgpg,
            total_protein_grams      = v.tpg
        FROM (VALUES
            (100,   0,   0, 100,  3,  3),
            (140, 140,  15,   0,  0, 15),
            (240, 140,  15, 100,  3, 18),
            (385, 140,  15, 140,  5, 20),
            (400, 200,  22, 140,  5, 27),
            (410, 140,  15, 210,  7, 22),
            (445, 200,  22, 140,  5, 27),
            (450, 250,  30, 140,  5, 35),
            (455, 140,  15, 210,  7, 22),
            (470, 200,  22, 210,  7, 29),
            (480, 140,  15, 280,  9, 24),
            (495, 250,  30, 140,  5, 35),
            (515, 200,  22, 210,  7, 29),
            (520, 250,  30, 210,  7, 37),
            (525, 140,  15, 280,  9, 24),
            (540, 200,  22, 280,  9, 31),
            (565, 250,  30, 210,  7, 37),
            (570, 300,  35, 210,  7, 42),
            (585, 200,  22, 280,  9, 31),
            (590, 250,  30, 280,  9, 39),
            (615, 300,  35, 210,  7, 42),
            (630, 360,  40, 210,  7, 47),
            (635, 250,  30, 280,  9, 39),
            (640, 300,  35, 280,  9, 44),
            (675, 360,  40, 210,  7, 47),
            (685, 300,  35, 280,  9, 44),
            (700, 360,  40, 280,  9, 49),
            (745, 360,  40, 280,  9, 49),
            (770, 360,  40, 350, 11, 51),
            (815, 360,  40, 350, 11, 51),
            (840, 360,  40, 420, 14, 54),
            (860, 450,  50, 350, 11, 61),
            (885, 360,  40, 420, 14, 54),
            (905, 450,  50, 350, 11, 61),
            (930, 450,  50, 420, 14, 64),
            (975, 450,  50, 420, 14, 64),
            (1000, 450, 50, 490, 16, 66),
            (1045, 450, 50, 490, 16, 66),
            (1090, 540, 60, 490, 16, 76),
            (1135, 540, 60, 490, 16, 76)
        ) AS v(cal, pgc, pgg, cgc, cgpg, tpg)
        WHERE meals.calories = v.cal
    """)


def downgrade() -> None:
    op.drop_column("meals", "total_protein_grams")
    op.drop_column("meals", "carb_group_protein_grams")
    op.drop_column("meals", "carb_group_calories")
    op.drop_column("meals", "protein_group_grams")
    op.drop_column("meals", "protein_group_calories")
