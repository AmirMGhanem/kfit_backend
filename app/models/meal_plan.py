import enum
import uuid

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPKMixin, UpdatedAtMixin
from app.models.meal import Meal, MealType


class MealPlanStatus(enum.Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class MealPlan(Base, UUIDPKMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    One meal-plan generation run for a client.

    Built from a ``calculation`` (the source of the calorie window). The calorie
    targets and the client's request (how many mains, whether a snack) are
    snapshotted here so the plan stays a faithful historical artifact even if the
    calculation is later recomputed.
    """

    __tablename__ = "meal_plans"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )
    calculation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculations.id"), nullable=False, index=True
    )

    # ── Snapshot of the targets / request at generation time ────────────────
    min_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    max_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    # Number of generic (main) meals requested; a snack is added on top.
    meals_count: Mapped[int] = mapped_column(Integer, nullable=False)
    include_snack: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    status: Mapped[MealPlanStatus] = mapped_column(
        SAEnum(MealPlanStatus, name="mealplanstatus"),
        nullable=False,
        server_default=MealPlanStatus.pending.value,
    )

    # ── Filled when status flips to ``ready`` ───────────────────────────────
    total_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_protein_calories: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["MealPlanItem"]] = relationship(
        "MealPlanItem",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        order_by="MealPlanItem.position",
    )


class MealPlanItem(Base, UUIDPKMixin, CreatedAtMixin):
    """
    A single meal selected by the agent for a plan.

    Nutrition and type are snapshotted from the catalog at selection time so the
    plan is reproducible even if the meal row later changes. A meal may appear
    more than once in a plan (different positions), so only ``(plan, position)``
    is unique — not ``(plan, meal)``.
    """

    __tablename__ = "meal_plan_items"
    __table_args__ = (
        UniqueConstraint("meal_plan_id", "position", name="uq_meal_plan_item_position"),
    )

    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meals.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Snapshot from the catalog at selection time ─────────────────────────
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meal_type: Mapped[MealType] = mapped_column(
        SAEnum(MealType, name="mealtype"), nullable=False
    )

    meal_plan: Mapped["MealPlan"] = relationship("MealPlan", back_populates="items")
    meal: Mapped["Meal"] = relationship("Meal")
