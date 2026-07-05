"""calculations table (BMR / TEE / calorie range)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────
    for name, values in [
        ("worktype",      ["daily", "partial", "none"]),
        ("nutritiongoal", ["weight_loss", "muscle_gain"]),
    ]:
        postgresql.ENUM(*values, name=name, create_type=False).create(
            op.get_bind(), checkfirst=True
        )

    # ── calculations ───────────────────────────────────────────────────────
    op.create_table(
        "calculations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id",     postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "gender",
            postgresql.ENUM("male", "female", "other",
                            name="gender", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "work_type",
            postgresql.ENUM("daily", "partial", "none",
                            name="worktype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "goal",
            postgresql.ENUM("weight_loss", "muscle_gain",
                            name="nutritiongoal", create_type=False),
            nullable=False,
        ),
        sa.Column("training_types", postgresql.JSONB(), nullable=False),

        sa.Column("bmr",          sa.Integer(), nullable=False),
        sa.Column("bmr_with_paf", sa.Integer(), nullable=False),
        sa.Column("tee",          sa.Integer(), nullable=False),
        sa.Column("min_calories", sa.Integer(), nullable=False),
        sa.Column("max_calories", sa.Integer(), nullable=False),

        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),

        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calculations_submission_id", "calculations", ["submission_id"]
    )
    op.create_index(
        "ix_calculations_client_id", "calculations", ["client_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_calculations_client_id", table_name="calculations")
    op.drop_index("ix_calculations_submission_id", table_name="calculations")
    op.drop_table("calculations")

    for name in ("nutritiongoal", "worktype"):
        postgresql.ENUM(name=name, create_type=False).drop(
            op.get_bind(), checkfirst=True
        )
