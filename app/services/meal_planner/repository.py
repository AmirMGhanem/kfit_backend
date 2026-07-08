"""
Database access for the meal planner — the only module that touches the ORM.

Steps call these functions; they never build queries themselves. This keeps the
pipeline logic pure and swappable, and concentrates all persistence concerns
(snapshotting, status transitions) in one place.

These are real queries against the existing models — this is DB *preparation*,
not external wiring. They become live the moment the pipeline is invoked with a
session.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.calculation import Calculation
from app.models.llm_request import LLMRequest
from app.models.meal import Meal, MealType
from app.models.meal_plan import MealPlan, MealPlanItem, MealPlanStatus
from app.models.submission import Submission
from app.services.meal_planner import targets as target_calc
from app.services.meal_planner.schemas import (
    MealCandidate,
    MealProposal,
    PlanContext,
    PlanTargets,
    ValidationResult,
)


async def fetch_targets(
    session: AsyncSession,
    calculation_id: uuid.UUID,
    *,
    meals_count: int,
    include_snack: bool,
) -> tuple[uuid.UUID, PlanTargets]:
    """Load the window, compute the rule targets, read the fruit preference.

    Returns (client_id, targets).
    """
    calc = await session.get(Calculation, calculation_id)
    if calc is None:
        raise ValueError(f"calculation {calculation_id} not found")

    mt = target_calc.compute_targets(calc.min_calories, calc.max_calories, meals_count)

    # Fruit preference lives in the originating submission's payload (R7).
    fruit_pref: str | None = None
    submission = await session.get(Submission, calc.submission_id)
    if submission is not None:
        raw = submission.payload.get("fruitPreference")
        fruit_pref = str(raw) if raw else None

    targets = PlanTargets(
        min_calories=calc.min_calories,
        max_calories=calc.max_calories,
        meals_count=meals_count,
        include_snack=include_snack,
        daily_calories=mt.daily_calories,
        free_calories=mt.free_calories,
        remaining_calories=mt.remaining_calories,
        meal_targets=mt.meal_targets,
        big_meal_position=mt.big_meal_position,
        tolerance=mt.tolerance,
        fruit_preference=fruit_pref,
    )
    return calc.client_id, targets


async def fetch_active_catalog(session: AsyncSession) -> list[MealCandidate]:
    """Active meals the agent may choose — excludes free-calorie items, which
    are attached by code, not selected by the model."""
    rows = (
        await session.execute(
            select(Meal).where(
                Meal.is_active.is_(True), Meal.meal_type != MealType.free
            )
        )
    ).scalars()
    return [
        MealCandidate(
            meal_id=m.id,
            name=m.name,
            calories=m.calories,
            protein_calories=m.protein_calories,
            total_protein_grams=m.total_protein_grams,
            meal_type=m.meal_type.value,
            has_fat_source=m.has_fat_source,
            suitable_as_big_meal=m.suitable_as_big_meal,
        )
        for m in rows
    ]


async def fetch_free_meal(session: AsyncSession, calories: int) -> Meal | None:
    """The free-calorie catalog row matching the code-computed bucket."""
    return (
        await session.execute(
            select(Meal).where(
                Meal.meal_type == MealType.free, Meal.calories == calories
            )
        )
    ).scalar_one_or_none()


async def save_ready_plan(
    session: AsyncSession,
    ctx: PlanContext,
    proposal: MealProposal,
    result: ValidationResult,
    model: str,
) -> uuid.UUID:
    """Persist a validated plan + its items, status=ready. Returns the plan id.

    Appends the free-calorie allowance as the final plan item (R1) so the plan's
    total lands in the window: meals (daily − free) + free = daily.
    """
    index = ctx.candidate_index()
    free_total = 0
    plan = MealPlan(
        client_id=ctx.client_id,
        calculation_id=ctx.calculation_id,
        min_calories=ctx.targets.min_calories,
        max_calories=ctx.targets.max_calories,
        free_calories=ctx.targets.free_calories,
        meals_count=ctx.targets.meals_count,
        include_snack=ctx.targets.include_snack,
        status=MealPlanStatus.ready,
        total_protein_calories=result.total_protein_calories,
        model=model,
    )
    max_pos = 0
    for pick in sorted(proposal.picks, key=lambda p: p.position):
        meal = index[pick.meal_id]  # validated to exist before we get here
        max_pos = max(max_pos, pick.position)
        plan.items.append(
            MealPlanItem(
                meal_id=meal.meal_id,
                position=pick.position,
                calories=meal.calories,
                protein_calories=meal.protein_calories,
                meal_type=MealType(meal.meal_type),
            )
        )

    # Free-calorie allowance as the last item (code-attached, value from targets).
    free_meal = await fetch_free_meal(session, ctx.targets.free_calories)
    if free_meal is not None:
        free_total = free_meal.calories
        plan.items.append(
            MealPlanItem(
                meal_id=free_meal.id,
                position=max_pos + 1,
                calories=free_meal.calories,
                protein_calories=None,
                meal_type=MealType.free,
            )
        )

    # Total includes the free item → lands in [min, max] (= daily).
    plan.total_calories = result.total_calories + free_total
    session.add(plan)
    await session.flush()
    return plan.id


async def save_failed_plan(
    session: AsyncSession,
    ctx: PlanContext,
    result: ValidationResult,
    model: str,
    error: str,
) -> uuid.UUID:
    """Persist a failed run (no items), status=failed, with the reason."""
    plan = MealPlan(
        client_id=ctx.client_id,
        calculation_id=ctx.calculation_id,
        min_calories=ctx.targets.min_calories,
        max_calories=ctx.targets.max_calories,
        free_calories=ctx.targets.free_calories,
        meals_count=ctx.targets.meals_count,
        include_snack=ctx.targets.include_snack,
        status=MealPlanStatus.failed,
        model=model,
        error=error,
    )
    session.add(plan)
    await session.flush()
    return plan.id


async def save_llm_request(**fields: Any) -> None:
    """
    Persist one LLM-call audit row in its own short-lived transaction, so it is
    committed independently of (and never rolls back) the generation. Best-effort
    — the caller swallows exceptions.
    """
    async with AsyncSessionLocal() as session:
        session.add(LLMRequest(**fields))
        await session.commit()
