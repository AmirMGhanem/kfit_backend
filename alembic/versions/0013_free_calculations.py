"""free_calculations table (standalone calculator history)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-08

Standalone calculator runs, decoupled from onboarded clients/submissions. Reuses
the existing gender/worktype/nutritiongoal enums (create_type=False). Records the
consultant who ran it (created_by_user_id) and a free-text customer name.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "free_calculations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "gender",
            postgresql.ENUM(
                "male", "female", "other", name="gender", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "work_type",
            postgresql.ENUM(
                "daily", "partial", "none", name="worktype", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "goal",
            postgresql.ENUM(
                "weight_loss", "muscle_gain", name="nutritiongoal", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("training_types", postgresql.JSONB(), nullable=False),
        sa.Column("bmr", sa.Integer(), nullable=False),
        sa.Column("bmr_with_paf", sa.Integer(), nullable=False),
        sa.Column("tee", sa.Integer(), nullable=False),
        sa.Column("min_calories", sa.Integer(), nullable=False),
        sa.Column("max_calories", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_free_calculations_created_by_user_id",
        "free_calculations",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_free_calculations_created_by_user_id",
        table_name="free_calculations",
    )
    op.drop_table("free_calculations")
