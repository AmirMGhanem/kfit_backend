"""
Consultant chat routes (polling model). All staff-gated; conversations are
private to their owning consultant.

  POST /chat/conversations                 create (optional client_id)
  GET  /chat/conversations                 list my conversations
  GET  /chat/conversations/{id}            conversation + messages (poll here)
  POST /chat/conversations/{id}/messages   ask → fires background job, returns ids
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.services.chat_assistant import repository, run_chat

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class NewConversationIn(BaseModel):
    client_id: uuid.UUID | None = None


class ConversationOut(BaseModel):
    id: str
    client_id: str | None
    title: str | None
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str | None
    status: str | None
    step: str | None
    sources: list[dict[str, Any]] | None
    created_at: str


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class AskIn(BaseModel):
    text: str


class AskOut(BaseModel):
    user_message_id: str
    assistant_message_id: str


def _conv(c: ChatConversation) -> ConversationOut:
    return ConversationOut(
        id=str(c.id),
        client_id=str(c.client_id) if c.client_id else None,
        title=c.title,
        created_at=c.created_at.isoformat(),
    )


def _msg(m: ChatMessage) -> MessageOut:
    return MessageOut(
        id=str(m.id),
        role=m.role,
        content=m.content,
        status=m.status,
        step=m.step,
        sources=m.sources,
        created_at=m.created_at.isoformat(),
    )


async def _owned(
    session: AsyncSession, conversation_id: uuid.UUID, user: User
) -> ChatConversation:
    conv = await repository.get_conversation(session, conversation_id)
    if conv is None or conv.consultant_id != user.id:
        raise HTTPException(404, "conversation not found")
    return conv


# ── Routes ──────────────────────────────────────────────────────────────────
@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: NewConversationIn,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> ConversationOut:
    conv = await repository.create_conversation(session, user.id, body.client_id)
    await session.commit()
    return _conv(conv)


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> list[ConversationOut]:
    convs = await repository.list_conversations(session, user.id)
    return [_conv(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> ConversationDetailOut:
    conv = await _owned(session, conversation_id, user)
    msgs = await repository.get_messages(session, conv.id)
    return ConversationDetailOut(
        **_conv(conv).model_dump(), messages=[_msg(m) for m in msgs]
    )


@router.post(
    "/conversations/{conversation_id}/messages", response_model=AskOut, status_code=201
)
async def send_message(
    conversation_id: uuid.UUID,
    body: AskIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_staff),
    session: AsyncSession = Depends(get_session),
) -> AskOut:
    conv = await _owned(session, conversation_id, user)
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "empty message")

    user_msg = await repository.add_message(session, conv.id, role="user", content=text)
    assistant_msg = await repository.add_message(
        session, conv.id, role="assistant", status="pending", step="ממתין…"
    )
    await session.commit()

    background_tasks.add_task(run_chat, assistant_msg.id, text)
    return AskOut(
        user_message_id=str(user_msg.id),
        assistant_message_id=str(assistant_msg.id),
    )
