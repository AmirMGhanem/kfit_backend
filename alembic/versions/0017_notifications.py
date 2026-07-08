"""notifications: alerts + per-user recipient state

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-08

A notification is an alert (churn risk, low motivation, AI insight, ...) fanned
out to staff via ``notification_recipients`` rows that carry per-user read and
archive state. ``dedup_key`` collapses repeated open alerts.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), server_default="info", nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(), server_default="system", nullable=False),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dedup_key", sa.String(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
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
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_client_id", "notifications", ["client_id"])
    op.create_index("ix_notifications_dedup_key", "notifications", ["dedup_key"])

    op.create_table(
        "notification_recipients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id", "user_id", name="uq_notification_recipient"
        ),
    )
    op.create_index(
        "ix_notification_recipients_notification_id",
        "notification_recipients",
        ["notification_id"],
    )
    op.create_index(
        "ix_notification_recipients_user_id",
        "notification_recipients",
        ["user_id"],
    )
    op.create_index(
        "ix_notif_recipient_user_unread",
        "notification_recipients",
        ["user_id", "read_at"],
    )
    op.create_index(
        "ix_notif_recipient_user_active",
        "notification_recipients",
        ["user_id", "archived_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notif_recipient_user_active",
        table_name="notification_recipients",
    )
    op.drop_index(
        "ix_notif_recipient_user_unread",
        table_name="notification_recipients",
    )
    op.drop_index(
        "ix_notification_recipients_user_id",
        table_name="notification_recipients",
    )
    op.drop_index(
        "ix_notification_recipients_notification_id",
        table_name="notification_recipients",
    )
    op.drop_table("notification_recipients")
    op.drop_index("ix_notifications_dedup_key", table_name="notifications")
    op.drop_index("ix_notifications_client_id", table_name="notifications")
    op.drop_table("notifications")
