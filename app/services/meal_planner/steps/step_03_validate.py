"""
Step 03 — Validate (deterministic, no LLM). The correctness guarantee.

Recomputes the totals from the catalog's own numbers and checks every hard
constraint. A proposal can only proceed to persistence if this returns ok=True.
No prompt here — this is pure code, and deliberately so: the calorie window is
enforced by arithmetic we control, never by the model.
"""

from __future__ import annotations

from app.services.meal_planner.schemas import (
    MealProposal,
    PlanContext,
    ValidationResult,
)


def validate(ctx: PlanContext, proposal: MealProposal) -> ValidationResult:
    index = ctx.candidate_index()
    t = ctx.targets
    errors: list[str] = []

    # 1. Every picked id must exist in the catalog.
    unknown = [p.meal_id for p in proposal.picks if p.meal_id not in index]
    for mid in unknown:
        errors.append(f"meal_id {mid} is not in the catalog")

    known = [p for p in proposal.picks if p.meal_id in index]
    meals = [index[p.meal_id] for p in known]

    # 2. Composition: main count + snack rule.
    mains = [m for m in meals if m.meal_type == "generic"]
    snacks = [m for m in meals if m.meal_type == "snack"]
    if len(mains) != t.meals_count:
        errors.append(
            f"expected {t.meals_count} main (generic) meal(s), got {len(mains)}"
        )
    expected_snacks = 1 if t.include_snack else 0
    if len(snacks) != expected_snacks:
        errors.append(f"expected {expected_snacks} snack meal(s), got {len(snacks)}")

    # 3. Distinct positions.
    positions = [p.position for p in known]
    if len(set(positions)) != len(positions):
        errors.append("duplicate positions in picks")

    # 4. Calorie window (authoritative totals, computed here).
    total_cal = sum(m.calories for m in meals)
    total_protein = sum(m.protein_calories or 0 for m in meals)
    if meals and not (t.min_calories <= total_cal <= t.max_calories):
        errors.append(
            f"total {total_cal} kcal is outside [{t.min_calories}, {t.max_calories}]"
        )

    return ValidationResult(
        ok=not errors,
        errors=errors,
        total_calories=total_cal,
        total_protein_calories=total_protein,
    )
