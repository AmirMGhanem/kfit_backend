from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPKMixin


class Notification(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    A single alert surfaced to staff. Fan-out to individual users happens via
    ``NotificationRecipient`` rows; one notification may target many users.

    ``severity``: info | warning | critical.
    ``source``: ai_assistant | analyzer | system | manual.
    ``dedup_key`` collapses repeated alerts (see the notifications service).
    """

    __tablename__ = "notifications"

    type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, server_default="info")
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String, nullable=False, server_default="system")
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Attribute is ``meta`` (SQLAlchemy reserves ``metadata``); column is "meta".
    meta: Mapped[dict[str, Any] | None] = mapped_column("meta", JSONB, nullable=True)

    recipients: Mapped[list[NotificationRecipient]] = relationship(
        "NotificationRecipient",
        back_populates="notification",
        cascade="all, delete-orphan",
    )


class NotificationRecipient(Base, UUIDPKMixin, CreatedAtMixin):
    """Per-user delivery + read/archive state for a ``Notification``."""

    __tablename__ = "notification_recipients"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notification: Mapped[Notification] = relationship(
        "Notification", back_populates="recipients"
    )

    __table_args__ = (
        UniqueConstraint(
            "notification_id", "user_id", name="uq_notification_recipient"
        ),
        Index("ix_notif_recipient_user_unread", "user_id", "read_at"),
        Index(
            "ix_notif_recipient_user_active",
            "user_id",
            "archived_at",
            "created_at",
        ),
    )
