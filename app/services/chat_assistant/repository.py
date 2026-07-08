"""Database access for the chat assistant."""

from __future__ import annotations

import uuid

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatConversation, ChatMessage

# Within one turn the user + assistant messages share a created_at (same
# transaction → same now()), so break ties with role: user before assistant.
_ROLE_ORDER = case((ChatMessage.role == "user", 0), else_=1)


async def create_conversation(
    session: AsyncSession,
    consultant_id: uuid.UUID,
    client_id: uuid.UUID | None,
    *,
    title: str | None = None,
) -> ChatConversation:
    conv = ChatConversation(
        consultant_id=consultant_id, client_id=client_id, title=title
    )
    session.add(conv)
    await session.flush()
    return conv


async def get_conversation(
    session: AsyncSession, conversation_id: uuid.UUID
) -> ChatConversation | None:
    return await session.get(ChatConversation, conversation_id)


async def list_conversations(
    session: AsyncSession, consultant_id: uuid.UUID
) -> list[ChatConversation]:
    return list(
        (
            await session.execute(
                select(ChatConversation)
                .where(ChatConversation.consultant_id == consultant_id)
                .order_by(ChatConversation.updated_at.desc())
            )
        ).scalars()
    )


async def get_messages(
    session: AsyncSession, conversation_id: uuid.UUID
) -> list[ChatMessage]:
    return list(
        (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.created_at, _ROLE_ORDER)
            )
        ).scalars()
    )


async def add_message(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    role: str,
    content: str | None = None,
    status: str | None = None,
    step: str | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        status=status,
        step=step,
    )
    session.add(msg)
    await session.flush()
    return msg


async def recent_history(
    session: AsyncSession, conversation_id: uuid.UUID, limit: int = 10
) -> list[tuple[str, str]]:
    """Last N completed messages (chronological) as (role, content) pairs."""
    msgs = (
        (
            await session.execute(
                select(ChatMessage)
                .where(
                    ChatMessage.conversation_id == conversation_id,
                    ChatMessage.content.is_not(None),
                )
                .order_by(ChatMessage.created_at.desc(), _ROLE_ORDER.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [(m.role, m.content) for m in reversed(msgs) if m.content]
