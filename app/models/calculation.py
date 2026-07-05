import enum
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin, UpdatedAtMixin
from app.models.client import Gender


class WorkType(enum.Enum):
    daily = "daily"
    partial = "partial"
    none = "none"


class NutritionGoal(enum.Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"


class Calculation(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "calculations"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SAEnum(Gender, name="gender"), nullable=False
    )
    work_type: Mapped[WorkType] = mapped_column(
        SAEnum(WorkType, name="worktype"), nullable=False
    )
    goal: Mapped[NutritionGoal] = mapped_column(
        SAEnum(NutritionGoal, name="nutritiongoal"), nullable=False
    )
    training_types: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )

    bmr: Mapped[int] = mapped_column(Integer, nullable=False)
    bmr_with_paf: Mapped[int] = mapped_column(Integer, nullable=False)
    tee: Mapped[int] = mapped_column(Integer, nullable=False)
    min_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    max_calories: Mapped[int] = mapped_column(Integer, nullable=False)
