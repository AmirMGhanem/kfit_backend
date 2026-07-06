"""submission_insights table + submission_id on llm_requests

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-06

Auto-generated welcome-call analysis (red flags / pain points / insights) per
onboarding submission. Also links llm_requests to a submission (the analyzer's
calls have no calculation_id).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM(
        "pending", "ready", "failed", name="insightstatus", create_type=False
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "submission_insights",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "ready",
                "failed",
                name="insightstatus",
                create_type=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "red_flags",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pain_points",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "insights",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_submission_insights_submission_id",
        "submission_insights",
        ["submission_id"],
    )
    op.create_index(
        "ix_submission_insights_client_id",
        "submission_insights",
        ["client_id"],
    )

    op.add_column(
        "llm_requests",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_llm_requests_submission_id", "llm_requests", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_requests_submission_id", table_name="llm_requests")
    op.drop_column("llm_requests", "submission_id")

    op.drop_index("ix_submission_insights_client_id", table_name="submission_insights")
    op.drop_index(
        "ix_submission_insights_submission_id", table_name="submission_insights"
    )
    op.drop_table("submission_insights")

    postgresql.ENUM(name="insightstatus", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
