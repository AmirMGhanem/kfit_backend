"""
Notification routes.

  GET  /notifications              list notifications for the current user (staff)
  GET  /notifications/unread-count unread count for the current user (staff)
  POST /notifications/{id}/read    mark one notification read (staff)
  POST /notifications/read-all     mark all unread read (staff)
  POST /notifications/{id}/archive archive one notification (staff)
  POST /notifications              create a manual notification (admin)

Reads and mutations are scoped to the authenticated user. Mutating routes own
the commit (the service layer only flushes).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_admin, require_staff
from app.models.user import User
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    body: str | None
    client_id: str | None
    client_name: str | None
    source: str
    created_at: str
    read: bool
    archived: bool
    meta: dict[str, Any] | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class UnreadCount(BaseModel):
    count: int


class NotificationCreate(BaseModel):
    type: str
    title: str
    severity: str | None = None
    body: str | None = None
    client_id: uuid.UUID | None = None
    dedup_key: str | None = None
    meta: dict[str, Any] | None = None
    target_user_ids: list[uuid.UUID] | None = None


def _out_from_dict(row: dict[str, Any]) -> NotificationOut:
    return NotificationOut(
        id=str(row["id"]),
        type=row["type"],
        severity=row["severity"],
        title=row["title"],
        body=row["body"],
        client_id=row["client_id"],
        client_name=row["client_name"],
        source=row["source"],
        created_at=row["created_at"],
        read=row["read"],
        archived=row["archived"],
        meta=row["meta"],
    )


@router.get("", response_model=NotificationList)
async def list_notifications(
    status: str = "all",
    type: str | None = None,
    severity: str | None = None,
    limit: int = 30,
    before: datetime | None = None,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> NotificationList:
    rows = await notifications_service.list_for_user(
        session,
        user.id,
        status=status,
        type=type,
        severity=severity,
        limit=limit,
        before=before,
    )
    count = await notifications_service.unread_count(session, user.id)
    return NotificationList(
        items=[_out_from_dict(r) for r in rows],
        unread_count=count,
    )


@router.get("/unread-count", response_model=UnreadCount)
async def get_unread_count(
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> UnreadCount:
    count = await notifications_service.unread_count(session, user.id)
    return UnreadCount(count=count)


@router.post("/{notification_id}/read", status_code=200)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    matched = await notifications_service.mark_read(session, user.id, notification_id)
    if not matched:
        raise HTTPException(404, "notification not found")
    await session.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    updated = await notifications_service.mark_all_read(session, user.id)
    await session.commit()
    return {"updated": updated}


@router.post("/{notification_id}/archive", status_code=204)
async def archive_notification(
    notification_id: uuid.UUID,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> None:
    matched = await notifications_service.archive(session, user.id, notification_id)
    if not matched:
        raise HTTPException(404, "notification not found")
    await session.commit()


@router.post("", response_model=NotificationOut, status_code=201)
async def create_notification(
    body: NotificationCreate,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> NotificationOut:
    notification = await notifications_service.create_notification(
        session,
        type=body.type,
        title=body.title,
        severity=body.severity or "info",
        body=body.body,
        client_id=body.client_id,
        source="manual",
        created_by=user.id,
        dedup_key=body.dedup_key,
        meta=body.meta,
        target_user_ids=body.target_user_ids,
    )
    await session.commit()

    rows = await notifications_service.list_for_user(
        session,
        user.id,
        status="all",
        limit=1,
    )
    for row in rows:
        if row["id"] == str(notification.id):
            return _out_from_dict(row)

    return NotificationOut(
        id=str(notification.id),
        type=notification.type,
        severity=notification.severity,
        title=notification.title,
        body=notification.body,
        client_id=str(notification.client_id) if notification.client_id else None,
        client_name=None,
        source=notification.source,
        created_at=notification.created_at.isoformat(),
        read=False,
        archived=False,
        meta=notification.meta,
    )
