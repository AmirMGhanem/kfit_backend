"""
Meal-planner pipeline orchestrator.

Wires the five steps into the propose → validate → repair loop:

    build_context
         │
         ▼
     propose ──▶ validate ──ok?──▶ persist_success
         ▲            │ no
         │            ▼
      repair ◀── (attempts < MAX)
         │  exhausted
         ▼
     persist_failure

This is the single public entry point. Wiring it into a router or a background
job later means: construct an LLMClient, get an AsyncSession, call run_pipeline.
Nothing here calls the network on its own — the LLM is injected.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.meal_planner import config
from app.services.meal_planner.llm.base import LLMClient
from app.services.meal_planner.schemas import PlanOutcome
from app.services.meal_planner.steps.step_01_build_context import build_context
from app.services.meal_planner.steps.step_02_propose import propose
from app.services.meal_planner.steps.step_03_validate import validate
from app.services.meal_planner.steps.step_04_repair import repair
from app.services.meal_planner.steps.step_05_persist import (
    persist_failure,
    persist_success,
)
from app.services.meal_planner.trace import calculation_id_var

logger = logging.getLogger(__name__)


async def run_pipeline(
    session: AsyncSession,
    calculation_id: uuid.UUID,
    *,
    meals_count: int,
    include_snack: bool,
    llm: LLMClient,
    builder_model: str | None = None,
    repair_model: str | None = None,
) -> PlanOutcome:
    """Generate and persist one meal plan. Returns the outcome (ready|failed).

    Fast ``builder_model`` makes the first proposal; stronger ``repair_model``
    only runs when validation rejects it. The model recorded on the plan is the
    one that produced the final (shipped) proposal.
    """
    builder_model = builder_model or config.BUILDER_MODEL
    repair_model = repair_model or config.REPAIR_MODEL
    calculation_id_var.set(str(calculation_id))

    ctx = await build_context(
        session,
        calculation_id,
        meals_count=meals_count,
        include_snack=include_snack,
    )
    logger.info(
        "meal-plan start calc=%s client=%s window=%d-%d meals=%d snack=%s catalog=%d",
        calculation_id,
        ctx.client_id,
        ctx.targets.min_calories,
        ctx.targets.max_calories,
        meals_count,
        include_snack,
        len(ctx.candidates),
    )

    proposal = await propose(ctx, llm, model=builder_model)
    result = validate(ctx, proposal)
    logger.info(
        "attempt 1 builder=%s picks=%d ok=%s total=%d errors=%s",
        builder_model,
        len(proposal.picks),
        result.ok,
        result.total_calories,
        result.errors,
    )

    attempts = 1
    while not result.ok and attempts <= config.MAX_REPAIR_ATTEMPTS:
        logger.info(
            "repair %d model=%s reason=%s", attempts + 1, repair_model, result.errors
        )
        proposal = await repair(ctx, proposal, result, llm, model=repair_model)
        result = validate(ctx, proposal)
        logger.info(
            "attempt %d repair=%s picks=%d ok=%s total=%d errors=%s",
            attempts + 1,
            repair_model,
            len(proposal.picks),
            result.ok,
            result.total_calories,
            result.errors,
        )
        attempts += 1

    # attempts == 1 means the builder's first proposal shipped; anything more
    # means repair produced the final one.
    final_model = builder_model if attempts == 1 else repair_model

    if result.ok:
        logger.info(
            "meal-plan READY total=%d protein=%d model=%s attempts=%d",
            result.total_calories,
            result.total_protein_calories,
            final_model,
            attempts,
        )
        return await persist_success(
            session, ctx, proposal, result, final_model, attempts
        )
    logger.warning("meal-plan FAILED attempts=%d errors=%s", attempts, result.errors)
    return await persist_failure(session, ctx, result, final_model, attempts)
