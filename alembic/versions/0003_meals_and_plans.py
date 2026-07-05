"""meals catalog + meal plans + plan items

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────
    for name, values in [
        ("mealtype",       ["generic", "snack"]),
        ("mealplanstatus", ["pending", "generating", "ready", "failed"]),
    ]:
        postgresql.ENUM(*values, name=name, create_type=False).create(
            op.get_bind(), checkfirst=True
        )

    # ── meals (catalog) ─────────────────────────────────────────────────────
    op.create_table(
        "meals",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("name",             sa.String(), nullable=False),
        sa.Column("calories",         sa.Integer(), nullable=False),
        sa.Column("protein_calories", sa.Integer(), nullable=True),
        sa.Column(
            "meal_type",
            postgresql.ENUM("generic", "snack", name="mealtype", create_type=False),
            server_default="generic", nullable=False,
        ),
        sa.Column(
            "payload", postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(),
            server_default=sa.text("true"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── meal_plans (one generation run) ─────────────────────────────────────
    op.create_table(
        "meal_plans",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("client_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("min_calories",  sa.Integer(), nullable=False),
        sa.Column("max_calories",  sa.Integer(), nullable=False),
        sa.Column("meals_count",   sa.Integer(), nullable=False),
        sa.Column(
            "include_snack", sa.Boolean(),
            server_default=sa.text("false"), nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "generating", "ready", "failed",
                name="mealplanstatus", create_type=False,
            ),
            server_default="pending", nullable=False,
        ),
        sa.Column("total_calories",         sa.Integer(), nullable=True),
        sa.Column("total_protein_calories", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),

        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),

        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["calculation_id"], ["calculations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_plans_client_id", "meal_plans", ["client_id"])
    op.create_index(
        "ix_meal_plans_calculation_id", "meal_plans", ["calculation_id"]
    )

    # ── meal_plan_items (agent output) ──────────────────────────────────────
    op.create_table(
        "meal_plan_items",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("meal_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position",     sa.Integer(), nullable=False),

        sa.Column("calories",         sa.Integer(), nullable=False),
        sa.Column("protein_calories", sa.Integer(), nullable=True),
        sa.Column(
            "meal_type",
            postgresql.ENUM("generic", "snack", name="mealtype", create_type=False),
            nullable=False,
        ),

        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["meal_plan_id"], ["meal_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meal_plan_id", "position", name="uq_meal_plan_item_position"
        ),
    )
    op.create_index(
        "ix_meal_plan_items_meal_plan_id", "meal_plan_items", ["meal_plan_id"]
    )
    op.create_index(
        "ix_meal_plan_items_meal_id", "meal_plan_items", ["meal_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_meal_plan_items_meal_id", table_name="meal_plan_items")
    op.drop_index("ix_meal_plan_items_meal_plan_id", table_name="meal_plan_items")
    op.drop_table("meal_plan_items")

    op.drop_index("ix_meal_plans_calculation_id", table_name="meal_plans")
    op.drop_index("ix_meal_plans_client_id", table_name="meal_plans")
    op.drop_table("meal_plans")

    op.drop_table("meals")

    for name in ("mealplanstatus", "mealtype"):
        postgresql.ENUM(name=name, create_type=False).drop(
            op.get_bind(), checkfirst=True
        )
