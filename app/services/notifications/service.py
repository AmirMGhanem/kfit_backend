"""Notification creation, delivery, and per-user read/archive state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.notification import Notification, NotificationRecipient
from app.models.user import User
from app.services.notifications.constants import SEVERITIES

_STAFF_ROLES = ("admin", "consultant")


async def create_notification(
    session: AsyncSession,
    *,
    type: str,
    title: str,
    severity: str = "info",
    body: str | None = None,
    client_id: uuid.UUID | None = None,
    source: str = "system",
    source_ref: str | None = None,
    created_by: uuid.UUID | None = None,
    dedup_key: str | None = None,
    meta: dict[str, Any] | None = None,
    target_user_ids: list[uuid.UUID] | None = None,
) -> Notification:
    """Create a notification and fan it out to recipients.

    Flushes (to obtain ids) but never commits — the caller owns the
    transaction boundary.
    """
    if severity not in SEVERITIES:
        severity = "info"

    if dedup_key:
        existing = await _find_open_by_dedup(session, dedup_key)
        if existing is not None:
            return existing

    notification = Notification(
        type=type,
        severity=severity,
        title=title,
        body=body,
        client_id=client_id,
        source=source,
        source_ref=source_ref,
        created_by=created_by,
        dedup_key=dedup_key,
        meta=meta,
    )
    session.add(notification)
    await session.flush()

    if target_user_ids is not None:
        user_ids = list(target_user_ids)
    else:
        user_ids = list(
            (
                await session.execute(
                    select(User.id).where(
                        User.is_active.is_(True),
                        User.role.in_(_STAFF_ROLES),
                    )
                )
            ).scalars()
        )

    for user_id in user_ids:
        session.add(
            NotificationRecipient(
                notification_id=notification.id,
                user_id=user_id,
            )
        )
    await session.flush()
    return notification


async def _find_open_by_dedup(
    session: AsyncSession, dedup_key: str
) -> Notification | None:
    """Return an existing OPEN notification (>=1 non-archived recipient)."""
    stmt = (
        select(Notification)
        .join(
            NotificationRecipient,
            NotificationRecipient.notification_id == Notification.id,
        )
        .where(
            Notification.dedup_key == dedup_key,
            NotificationRecipient.archived_at.is_(None),
        )
        .order_by(Notification.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(NotificationRecipient)
        .where(
            NotificationRecipient.user_id == user_id,
            NotificationRecipient.read_at.is_(None),
            NotificationRecipient.archived_at.is_(None),
        )
    )
    return int((await session.execute(stmt)).scalar_one())


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str = "all",
    type: str | None = None,
    severity: str | None = None,
    limit: int = 30,
    before: datetime | None = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(
            Notification,
            NotificationRecipient.read_at,
            NotificationRecipient.archived_at,
            Client.full_name,
        )
        .join(
            NotificationRecipient,
            NotificationRecipient.notification_id == Notification.id,
        )
        .outerjoin(Client, Client.id == Notification.client_id)
        .where(NotificationRecipient.user_id == user_id)
    )

    if status == "unread":
        stmt = stmt.where(
            NotificationRecipient.read_at.is_(None),
            NotificationRecipient.archived_at.is_(None),
        )
    elif status == "archived":
        stmt = stmt.where(NotificationRecipient.archived_at.is_not(None))
    else:  # "all" — active (non-archived) only
        stmt = stmt.where(NotificationRecipient.archived_at.is_(None))

    if type is not None:
        stmt = stmt.where(Notification.type == type)
    if severity is not None:
        stmt = stmt.where(Notification.severity == severity)
    if before is not None:
        stmt = stmt.where(Notification.created_at < before)

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).all()
    items: list[dict[str, Any]] = []
    for notification, read_at, archived_at, client_name in rows:
        items.append(
            {
                "id": str(notification.id),
                "type": notification.type,
                "severity": notification.severity,
                "title": notification.title,
                "body": notification.body,
                "client_id": (
                    str(notification.client_id)
                    if notification.client_id is not None
                    else None
                ),
                "client_name": client_name,
                "source": notification.source,
                "created_at": notification.created_at.isoformat(),
                "read": read_at is not None,
                "archived": archived_at is not None,
                "meta": notification.meta,
            }
        )
    return items


async def mark_read(
    session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID
) -> bool:
    recipient = await _get_recipient(session, user_id, notification_id)
    if recipient is None:
        return False
    if recipient.read_at is None:
        recipient.read_at = datetime.now(UTC)
        await session.flush()
    return True


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(NotificationRecipient).where(
        NotificationRecipient.user_id == user_id,
        NotificationRecipient.read_at.is_(None),
        NotificationRecipient.archived_at.is_(None),
    )
    recipients = list((await session.execute(stmt)).scalars())
    now = datetime.now(UTC)
    for recipient in recipients:
        recipient.read_at = now
    await session.flush()
    return len(recipients)


async def archive(
    session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID
) -> bool:
    recipient = await _get_recipient(session, user_id, notification_id)
    if recipient is None:
        return False
    recipient.archived_at = datetime.now(UTC)
    await session.flush()
    return True


async def _get_recipient(
    session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID
) -> NotificationRecipient | None:
    stmt = select(NotificationRecipient).where(
        NotificationRecipient.user_id == user_id,
        NotificationRecipient.notification_id == notification_id,
    )
    return (await session.execute(stmt)).scalars().first()
