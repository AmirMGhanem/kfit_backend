import enum
from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPKMixin


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

    # Structured nutrition breakdown (from kfit_meal_protein_table.csv)
    protein_group_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_group_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carb_group_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carb_group_protein_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_protein_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full component detail (from kfit_meal_full_components_table.xlsx)
    meal_structure: Mapped[str | None] = mapped_column(String, nullable=True)
    veg_group_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat_group_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat_source: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    # Fat rule (R5/R6): the big meal must contain a built-in fat source.
    has_fat_source: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    suitable_as_big_meal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # Prepared meal content — populated / fetched out-of-band.
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Soft toggle so the agent can exclude a meal without deleting history.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
