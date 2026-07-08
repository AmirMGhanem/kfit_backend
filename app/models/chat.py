import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPKMixin


class ChatConversation(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    A consultant's chat thread. Private to its owner (``consultant_id``) and
    optionally scoped to a client, which pulls that client's records into the
    assistant's context.
    """

    __tablename__ = "chat_conversations"

    consultant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base, UUIDPKMixin, CreatedAtMixin):
    """
    One message. User messages carry the question. Assistant messages are polled
    job rows: ``status`` (pending→generating→ready|failed) + ``step`` drive the
    thinking indicator; ``content`` + ``sources`` fill in when ready.
    """

    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    step: Mapped[str | None] = mapped_column(String, nullable=True)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversation: Mapped["ChatConversation"] = relationship(
        "ChatConversation", back_populates="messages"
    )
