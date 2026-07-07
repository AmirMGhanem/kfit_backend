"""
Step 03 — Validate (deterministic, no LLM). The correctness guarantee.

Recomputes everything from the catalog's own numbers and enforces the rules that
must be exact (never trusted to the model):

  • composition: exactly meals_count generic meals + the snack rule
  • per-meal calorie bands (R2): each main meal within its target ± tolerance,
    where position 1 = small (⅓) and position 2 = big (⅔)
  • snack folds into the big meal (R6): the big meal + snack must hit the big
    target ± tolerance
  • the big meal must carry a built-in fat source (R5)
  • the whole day (meals + snack + free calories) lands in [min, max]

Protein maximization, tiebreakers and preferences (R3/R4/R7/R9) are judgment —
they live in the prompt, not here.
"""

from __future__ import annotations

from app.services.meal_planner.schemas import (
    MealCandidate,
    MealProposal,
    PlanContext,
    ValidationResult,
)


def validate(ctx: PlanContext, proposal: MealProposal) -> ValidationResult:
    index = ctx.candidate_index()
    t = ctx.targets
    tol = t.tolerance
    errors: list[str] = []

    # 1. Every picked id must exist in the catalog.
    for p in proposal.picks:
        if p.meal_id not in index:
            errors.append(f"meal_id {p.meal_id} is not in the catalog")

    known = [p for p in proposal.picks if p.meal_id in index]
    by_pos: dict[int, MealCandidate] = {p.position: index[p.meal_id] for p in known}
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

    snack_cal = sum(m.calories for m in snacks)
    big_pos = t.big_meal_position

    # 4. Per-meal calorie bands (R2), snack folded into the big meal (R6).
    for pos, target in t.meal_targets.items():
        meal = by_pos.get(pos)
        if meal is None:
            errors.append(f"missing meal at position {pos}")
            continue
        got = meal.calories + (snack_cal if pos == big_pos else 0)
        label = "big" if pos == big_pos else f"meal {pos}"
        if not (target - tol <= got <= target + tol):
            plus = " + snack" if pos == big_pos and snack_cal else ""
            errors.append(
                f"{label} calories {got}{plus} outside "
                f"{target}±{tol} ({target - tol}-{target + tol})"
            )

    # 5. The big meal must carry a built-in fat source (R5).
    if big_pos is not None:
        big = by_pos.get(big_pos)
        if big is not None and not big.has_fat_source:
            errors.append(f"big meal (position {big_pos}) must contain a fat source")

    # 6. Whole day: meals + snack + free calories within the window.
    meals_total = sum(m.calories for m in meals)
    day_total = meals_total + t.free_calories
    if meals and not (t.min_calories <= day_total <= t.max_calories):
        errors.append(
            f"day total {day_total} (meals {meals_total} + free {t.free_calories}) "
            f"outside [{t.min_calories}, {t.max_calories}]"
        )

    total_protein = sum(m.protein_calories or 0 for m in meals)
    return ValidationResult(
        ok=not errors,
        errors=errors,
        total_calories=meals_total,
        total_protein_calories=total_protein,
    )
