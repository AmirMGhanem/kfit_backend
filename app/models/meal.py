import enum
from typing import Any

from sqlalchemy import Boolean, Enum as SAEnum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin, UpdatedAtMixin


class MealType(enum.Enum):
    generic = "generic"
    snack = "snack"


class Meal(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    A pre-prepared meal in the catalog.

    Only ``calories`` and ``protein_calories`` are used by the meal-planning
    agent; the rest of the meal content (recipe, ingredients, display name,
    image, …) lives in ``payload`` and is populated / fetched separately.

    ``protein_calories`` is stored exactly as the source provides it — the
    protein contribution in calories — and is NULL where the source does not
    specify a protein portion.
    """

    __tablename__ = "meals"

    name: Mapped[str] = mapped_column(String, nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meal_type: Mapped[MealType] = mapped_column(
        SAEnum(MealType, name="mealtype"),
        nullable=False,
        server_default=MealType.generic.value,
    )

    # Prepared meal content — populated / fetched out-of-band.
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Soft toggle so the agent can exclude a meal without deleting history.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
