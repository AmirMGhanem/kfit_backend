import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.client import Client


class SubmissionType(enum.Enum):
    onboarding = "onboarding"


class Submission(Base, UUIDPKMixin):
    __tablename__ = "submissions"

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True, index=True
    )
    type: Mapped[SubmissionType] = mapped_column(
        SAEnum(SubmissionType, name="submissiontype"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped["Client | None"] = relationship(
        "Client", back_populates="submissions"
    )
