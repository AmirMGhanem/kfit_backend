"""
Step 05 — Persist (deterministic, no LLM).

Writes the final state to the DB via the repository and returns a PlanOutcome.
Success → meal_plan + items, status=ready. Failure → meal_plan, status=failed,
with the reason. No prompt here.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.meal_planner import repository
from app.services.meal_planner.schemas import (
    MealProposal,
    PlanContext,
    PlanOutcome,
    ValidationResult,
)


async def persist_success(
    session: AsyncSession,
    ctx: PlanContext,
    proposal: MealProposal,
    result: ValidationResult,
    model: str,
    attempts: int,
) -> PlanOutcome:
    plan_id = await repository.save_ready_plan(session, ctx, proposal, result, model)
    return PlanOutcome(
        status="ready",
        meal_plan_id=plan_id,
        total_calories=result.total_calories,
        total_protein_calories=result.total_protein_calories,
        attempts=attempts,
    )


async def persist_failure(
    session: AsyncSession,
    ctx: PlanContext,
    result: ValidationResult,
    model: str,
    attempts: int,
) -> PlanOutcome:
    error = "; ".join(result.errors) or "unknown validation failure"
    plan_id = await repository.save_failed_plan(session, ctx, result, model, error)
    return PlanOutcome(
        status="failed",
        meal_plan_id=plan_id,
        attempts=attempts,
        error=error,
    )
