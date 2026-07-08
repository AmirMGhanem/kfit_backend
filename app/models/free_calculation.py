import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin
from app.models.calculation import NutritionGoal, WorkType
from app.models.client import Gender


class FreeCalculation(Base, UUIDPKMixin, CreatedAtMixin):
    """Standalone calculator runs, not tied to an onboarded client/submission.

    Records who ran the calculation and a free-text customer name so consultants
    can use the calculator for prospects who haven't onboarded yet.
    """

    __tablename__ = "free_calculations"

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SAEnum(Gender, name="gender", create_type=False), nullable=False
    )
    work_type: Mapped[WorkType] = mapped_column(
        SAEnum(WorkType, name="worktype", create_type=False), nullable=False
    )
    goal: Mapped[NutritionGoal] = mapped_column(
        SAEnum(NutritionGoal, name="nutritiongoal", create_type=False), nullable=False
    )
    training_types: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    bmr: Mapped[int] = mapped_column(Integer, nullable=False)
    bmr_with_paf: Mapped[int] = mapped_column(Integer, nullable=False)
    tee: Mapped[int] = mapped_column(Integer, nullable=False)
    min_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    max_calories: Mapped[int] = mapped_column(Integer, nullable=False)
