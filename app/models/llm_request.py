import uuid
from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin


class LLMRequest(Base, UUIDPKMixin, CreatedAtMixin):
    """
    An audit record of one LLM call made by the meal-planner.

    Written best-effort by the OpenAI adapter (a failure to log never breaks a
    generation). ``calculation_id`` is a soft link — set from a contextvar the
    pipeline populates — so all calls for one generation can be grouped.
    """

    __tablename__ = "llm_requests"

    calculation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # success | error

    # Full prompt sent (list of {role, content}) and the model's structured reply.
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Raw meal_ids the model returned, and any dropped for not being valid UUIDs.
    raw_meal_ids: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    dropped_meal_ids: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
