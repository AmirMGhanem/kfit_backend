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
from app.services.meal_planner.schemas import (
    MealProposal,
    PlanOutcome,
    PlanTargets,
    ValidationResult,
)
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

# One (proposal, validation result, model) triple produced by one attempt of
# the propose→validate→repair loop.
Candidate = tuple[MealProposal, ValidationResult, str]


# ── Pure, unit-testable decision logic (no I/O, no LLM) ─────────────────────
def drift_for(day_total: int, targets: PlanTargets) -> int:
    """0 if ``day_total`` lands in [min, max]; else the distance to the
    nearer edge of the window."""
    if targets.min_calories <= day_total <= targets.max_calories:
        return 0
    return min(
        abs(day_total - targets.min_calories),
        abs(day_total - targets.max_calories),
    )


def build_drift_note(day_total: int, targets: PlanTargets) -> str:
    """One-line, English explanation for a best-effort (drifted) plan."""
    edge = (
        targets.min_calories
        if day_total < targets.min_calories
        else targets.max_calories
    )
    diff = day_total - edge
    sign = "+" if diff > 0 else ""
    return (
        "No meal combination matched the target exactly — shipped the "
        f"closest available: day {day_total} kcal vs target "
        f"{targets.min_calories}-{targets.max_calories} ({sign}{diff} kcal)."
    )


def select_best_candidate(
    candidates: list[Candidate], targets: PlanTargets
) -> Candidate | None:
    """Pick the structurally-valid candidate with the least calorie drift.

    A candidate is structurally valid when ``result.structural_errors`` is
    empty — regardless of any remaining calorie_errors. Ties keep the first
    (earliest-attempted) candidate. Returns ``None`` if no candidate is
    structurally valid.
    """
    best: Candidate | None = None
    best_drift: int | None = None
    for candidate in candidates:
        _, result, _ = candidate
        if result.structural_errors:
            continue
        drift = drift_for(result.day_total, targets)
        if best is None or drift < best_drift:  # type: ignore[operator]
            best = candidate
            best_drift = drift
    return best


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
    candidates: list[Candidate] = [(proposal, result, builder_model)]
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
        candidates.append((proposal, result, repair_model))
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

    best = select_best_candidate(candidates, ctx.targets)
    if best is not None:
        best_proposal, best_result, best_model = best
        drift = drift_for(best_result.day_total, ctx.targets)
        # Only annotate a plan whose DAY total fell outside the range. An
        # in-range day total is valid even if per-meal bands weren't all met
        # exactly — no note in that case.
        note = (
            build_drift_note(best_result.day_total, ctx.targets) if drift > 0 else None
        )
        logger.info(
            "meal-plan READY (drift=%d) total=%d protein=%d model=%s attempts=%d "
            "note=%r",
            drift,
            best_result.total_calories,
            best_result.total_protein_calories,
            best_model,
            attempts,
            note,
        )
        return await persist_success(
            session, ctx, best_proposal, best_result, best_model, attempts, note=note
        )

    logger.warning("meal-plan FAILED attempts=%d errors=%s", attempts, result.errors)
    return await persist_failure(session, ctx, result, final_model, attempts)
