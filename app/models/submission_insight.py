import enum
import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPKMixin


class InsightStatus(enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class SubmissionInsight(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    AI analysis of one onboarding submission — talking points for the
    consultant's welcome call. Auto-generated (async) after the client submits.

    Each of the three buckets is a JSONB list of ``{title, detail}`` items, in
    Hebrew. An empty ``red_flags`` list is meaningful ("no concerns"), not a bug.
    """

    __tablename__ = "submission_insights"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )
    status: Mapped[InsightStatus] = mapped_column(
        SAEnum(InsightStatus, name="insightstatus"),
        nullable=False,
        server_default=InsightStatus.pending.value,
    )

    red_flags: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    pain_points: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    insights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    model: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
