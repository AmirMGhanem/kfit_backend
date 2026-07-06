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
    """Load the calorie window from the calculation. Returns (client_id, targets)."""
    calc = await session.get(Calculation, calculation_id)
    if calc is None:
        raise ValueError(f"calculation {calculation_id} not found")

    targets = PlanTargets(
        min_calories=calc.min_calories,
        max_calories=calc.max_calories,
        meals_count=meals_count,
        include_snack=include_snack,
        protein_calories_target=None,  # no protein target column yet
    )
    return calc.client_id, targets


async def fetch_active_catalog(session: AsyncSession) -> list[MealCandidate]:
    """All active meals, reduced to what the agent needs to choose."""
    rows = (
        await session.execute(select(Meal).where(Meal.is_active.is_(True)))
    ).scalars()
    return [
        MealCandidate(
            meal_id=m.id,
            name=m.name,
            calories=m.calories,
            protein_calories=m.protein_calories,
            meal_type=m.meal_type.value,
        )
        for m in rows
    ]


async def save_ready_plan(
    session: AsyncSession,
    ctx: PlanContext,
    proposal: MealProposal,
    result: ValidationResult,
    model: str,
) -> uuid.UUID:
    """Persist a validated plan + its items, status=ready. Returns the plan id."""
    index = ctx.candidate_index()
    plan = MealPlan(
        client_id=ctx.client_id,
        calculation_id=ctx.calculation_id,
        min_calories=ctx.targets.min_calories,
        max_calories=ctx.targets.max_calories,
        meals_count=ctx.targets.meals_count,
        include_snack=ctx.targets.include_snack,
        status=MealPlanStatus.ready,
        total_calories=result.total_calories,
        total_protein_calories=result.total_protein_calories,
        model=model,
    )
    for pick in sorted(proposal.picks, key=lambda p: p.position):
        meal = index[pick.meal_id]  # validated to exist before we get here
        plan.items.append(
            MealPlanItem(
                meal_id=meal.meal_id,
                position=pick.position,
                calories=meal.calories,
                protein_calories=meal.protein_calories,
                meal_type=MealType(meal.meal_type),
            )
        )
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
