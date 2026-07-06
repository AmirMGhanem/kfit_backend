"""llm_requests audit table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-06

Stores one row per LLM call made by the meal-planner: prompt, raw output,
token usage, latency, and dropped meal_ids. Written best-effort by the adapter.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("calculation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("messages", postgresql.JSONB(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("raw_meal_ids", postgresql.JSONB(), nullable=True),
        sa.Column("dropped_meal_ids", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_requests_calculation_id", "llm_requests", ["calculation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_llm_requests_calculation_id", table_name="llm_requests")
    op.drop_table("llm_requests")
