"""
Deterministic target computation for the meal planner (R1, R2, R6).

Pure functions, no I/O — the calorie arithmetic the rules require is computed in
code, never left to the LLM. Given the calorie window, this produces:

  • free calories (R1): 10% of daily, rounded to the nearest of {120,150,200,250}
  • remaining = daily − free
  • per-meal calorie targets (R2): for 2 meals, small=⅓ and big=⅔ of remaining
  • the big-meal position (the ⅔ meal that must carry a fat source, R5)
  • the per-meal tolerance: min(50 kcal, 3% of daily)

Snack handling (R6) is by convention: the snack's calories come out of the big
meal's budget, so the validator checks (big meal + snack) against the big-meal
target — see step_03_validate.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.meal_planner import config


@dataclass(frozen=True)
class MealTargets:
    daily_calories: int
    free_calories: int
    remaining_calories: int
    # Per-meal calorie targets, indexed by position (1-based): {1: small, 2: big}
    meal_targets: dict[int, int]
    # Position of the big meal that must carry a fat source (None if N != 2).
    big_meal_position: int | None
    tolerance: int


def _daily_calories(min_cal: int, max_cal: int) -> int:
    basis = config.DAILY_CALORIES_BASIS
    if basis == "min":
        return min_cal
    if basis == "max":
        return max_cal
    return round((min_cal + max_cal) / 2)


def round_to_bucket(value: float) -> int:
    """Nearest bucket; on an exact tie, round DOWN (weight-loss default, R1)."""
    buckets = sorted(config.FREE_CALORIE_BUCKETS)
    best = buckets[0]
    best_dist = abs(value - best)
    for b in buckets[1:]:
        d = abs(value - b)
        if d < best_dist:  # strictly closer; ties keep the smaller (already set)
            best, best_dist = b, d
    return best


def compute_targets(min_cal: int, max_cal: int, meals_count: int) -> MealTargets:
    daily = _daily_calories(min_cal, max_cal)
    free = round_to_bucket(daily * config.FREE_CALORIE_FRACTION)
    remaining = daily - free
    tolerance = min(config.TOLERANCE_ABS, round(daily * config.TOLERANCE_PCT))

    if meals_count == 2:
        small_frac, big_frac = config.MEAL_SPLIT
        big = round(remaining * big_frac)
        small = remaining - big  # exact complement, ~⅓
        meal_targets = {1: small, 2: big}
        big_pos = 2
    else:
        # Fallback for non-standard counts: even split, no designated big meal.
        each = round(remaining / meals_count) if meals_count else remaining
        meal_targets = {i + 1: each for i in range(meals_count)}
        big_pos = None

    return MealTargets(
        daily_calories=daily,
        free_calories=free,
        remaining_calories=remaining,
        meal_targets=meal_targets,
        big_meal_position=big_pos,
        tolerance=tolerance,
    )
