import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.submission import Submission


class Gender(enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class ClientStatus(enum.Enum):
    lead = "lead"
    onboarding = "onboarding"
    active = "active"
    paused = "paused"
    churned = "churned"


class Client(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "clients"

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(
        SAEnum(Gender, name="gender"), nullable=True
    )
    status: Mapped[ClientStatus] = mapped_column(
        SAEnum(ClientStatus, name="clientstatus"),
        nullable=False,
        default=ClientStatus.lead,
    )
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="client"
    )
