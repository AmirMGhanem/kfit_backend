"""Nutrition calculator — line-for-line port of kfit/src/lib/calculatorUtils.js.

Exact-parity guarantees:
  - Constants identical (BMR multipliers, PAF, resistance cals, goal ranges).
  - Formulas identical: aerobic = (time/10)*(sessions/7)*weight; resistance =
    cals_per_session*(sessions/7); hiit = (time/8)*(sessions/7)*weight*1.2.
  - Rounding uses floor(x + 0.5) to match JS Math.round (round-half-up for
    positives), NOT Python's banker's round(). They diverge on x.5 cases.
  - `bmr` is accepted by calorie-range computation but ignored, mirroring the
    original implementation quirk.
"""
from math import floor
from typing import Literal

from pydantic import BaseModel, Field

# ── Constants (ported verbatim from CALCULATION_CONFIG) ───────────────────
BMR_MULTIPLIERS: dict[str, int] = {"male": 30, "female": 25}

PHYSICAL_ACTIVITY_FACTORS: dict[str, float] = {
    "daily": 1.1,
    "partial": 1.05,
    "none": 1.0,
}

RESISTANCE_CALORIES_PER_SESSION: dict[str, int] = {"male": 200, "female": 150}

GOAL_RANGES: dict[str, dict[str, float]] = {
    "weight_loss": {"min": 0.70, "max": 0.75},
    "muscle_gain": {"min": 1.00, "max": 1.10},
}

# ── Input/output types ────────────────────────────────────────────────────
Gender = Literal["male", "female"]
WorkType = Literal["daily", "partial", "none"]
NutritionGoal = Literal["weight_loss", "muscle_gain"]
TrainingKind = Literal["aerobic", "resistance", "hiit", "none"]


class TrainingInput(BaseModel):
    type: TrainingKind
    sessions: float = 0.0
    time: float = 0.0  # used only for aerobic/hiit; ignored for resistance/none


class CalculatorInputs(BaseModel):
    weight: float = Field(gt=0)
    gender: Gender
    work_type: WorkType
    goal: NutritionGoal
    training_types: list[TrainingInput]


class CalculationResult(BaseModel):
    bmr: int
    bmr_with_paf: int
    tee: int
    min_calories: int
    max_calories: int


# ── JS-parity round ───────────────────────────────────────────────────────
def _js_round(x: float) -> int:
    """Match JS Math.round (round-half-up for positive values)."""
    return int(floor(x + 0.5))


# ── Pipeline steps ────────────────────────────────────────────────────────
def _bmr(weight: float, gender: Gender) -> float:
    return weight * BMR_MULTIPLIERS[gender]


def _apply_paf(bmr: float, work_type: WorkType) -> float:
    return bmr * PHYSICAL_ACTIVITY_FACTORS[work_type]


def _training_calories(
    training: TrainingInput, gender: Gender, weight: float
) -> float:
    sessions = training.sessions
    if training.type == "aerobic":
        return (training.time / 10) * (sessions / 7) * weight
    if training.type == "resistance":
        return RESISTANCE_CALORIES_PER_SESSION[gender] * (sessions / 7)
    if training.type == "hiit":
        return (training.time / 8) * (sessions / 7) * weight * 1.2
    # "none" or anything else
    return 0.0


def _tee(
    trainings: list[TrainingInput],
    baseline: float,
    gender: Gender,
    weight: float,
) -> float:
    return baseline + sum(
        _training_calories(t, gender, weight) for t in trainings
    )


def _calorie_range(tee: float, goal: NutritionGoal) -> tuple[float, float]:
    r = GOAL_RANGES[goal]
    return tee * r["min"], tee * r["max"]


# ── Top-level entry — mirrors JS calculateNutrition ───────────────────────
def calculate(inputs: CalculatorInputs) -> CalculationResult:
    bmr = _bmr(inputs.weight, inputs.gender)
    bmr_paf = _apply_paf(bmr, inputs.work_type)
    tee = _tee(inputs.training_types, bmr_paf, inputs.gender, inputs.weight)
    cmin, cmax = _calorie_range(tee, inputs.goal)
    return CalculationResult(
        bmr=_js_round(bmr),
        bmr_with_paf=_js_round(bmr_paf),
        tee=_js_round(tee),
        min_calories=_js_round(cmin),
        max_calories=_js_round(cmax),
    )
