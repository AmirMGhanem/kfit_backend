"""initial schema — clients + submissions

Revision ID: 0001
Revises:
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────
    for name, values in [
        ("gender",         ["male", "female", "other"]),
        ("clientstatus",   ["lead", "onboarding", "active", "paused", "churned"]),
        ("submissiontype", ["onboarding"]),
    ]:
        postgresql.ENUM(*values, name=name, create_type=False).create(
            op.get_bind(), checkfirst=True
        )

    # ── clients ────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email",     sa.String(), nullable=True),
        sa.Column("phone",     sa.String(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "gender",
            postgresql.ENUM("male", "female", "other",
                            name="gender", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("lead", "onboarding", "active", "paused", "churned",
                            name="clientstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("source", sa.String(), nullable=True),
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
    op.create_index("ix_clients_email", "clients", ["email"])

    # ── submissions ────────────────────────────────────────────────────────
    op.create_table(
        "submissions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "type",
            postgresql.ENUM("onboarding", name="submissiontype", create_type=False),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submissions_client_id", "submissions", ["client_id"])


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("clients")

    for name in ("submissiontype", "clientstatus", "gender"):
        postgresql.ENUM(name=name, create_type=False).drop(
            op.get_bind(), checkfirst=True
        )
