"""Notifications service — creation, fan-out, and per-user read/archive state."""

from app.services.notifications.service import (
    archive,
    create_notification,
    list_for_user,
    mark_all_read,
    mark_read,
    unread_count,
)

__all__ = [
    "archive",
    "create_notification",
    "list_for_user",
    "mark_all_read",
    "mark_read",
    "unread_count",
]
