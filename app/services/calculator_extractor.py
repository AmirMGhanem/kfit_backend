"""Map onboarding answers (dict) → CalculatorInputs.

Returns None when any hard-required input is missing or invalid. The submission
itself always succeeds; calculation is best-effort.

Required from the wizard (must be present, non-empty, valid enum value):
  - weight           (number-as-string, > 0)
  - gender           ("male" | "female")
  - activityLevel    ("very-low" | "low" | "medium" | "high")
  - nutritionGoal    ("weight-loss" | "muscle-gain")
                     → other goal options ("body-toning", "health-energy",
                       "control-routine") are valid wizard answers but the
                       calculator doesn't model them; calc is skipped.

Soft (used when present, defaulted otherwise):
  - willExercise     ("yes" | "no" | "not-sure")
  - exerciseType     ("home" | "gym" | "walking" | "mixed" | "not-sure")
  - exerciseDays     ("1" | "2" | "3" | "4-plus")
"""
from typing import Any

from app.services.nutrition_calculator import CalculatorInputs, TrainingInput

# ── Semantic maps ─────────────────────────────────────────────────────────
# Wizard's 4-tier activity → calculator's 3-tier PAF.
# Sedentary office and "light movement" both collapse into PAF 1.0 (none).
_ACTIVITY_TO_WORKTYPE: dict[str, str] = {
    "very-low": "none",
    "low": "none",
    "medium": "partial",
    "high": "daily",
}

# Wizard pills → numeric sessions/week. "4-plus" is open-ended, take the
# lower bound (4) — conservative.
_DAYS_TO_SESSIONS: dict[str, float] = {
    "1": 1.0,
    "2": 2.0,
    "3": 3.0,
    "4-plus": 4.0,
}

# Wizard's goal value → calculator's goal enum. Hyphen-form on the wire,
# underscore-form internally. The calculator models only cut vs surplus;
# everything that isn't explicit muscle-gain is treated as cut (weight_loss),
# because body-toning, health-energy, and control-routine all imply
# maintenance-or-deficit intent — a conservative cut is the safe default.
_GOAL_MAP: dict[str, str] = {
    "weight-loss":     "weight_loss",
    "muscle-gain":     "muscle_gain",
    "body-toning":     "weight_loss",   # recomp / mild deficit
    "health-energy":   "weight_loss",   # wellness — conservative
    "control-routine": "weight_loss",   # behavior-led — conservative
}

# Default minutes/session for home/walking aerobic when the wizard doesn't
# ask for time-per-session.
_AEROBIC_DEFAULT_TIME = 30.0


def extract(answers: dict[str, Any]) -> CalculatorInputs | None:
    try:
        weight_raw = answers.get("weight")
        weight = float(weight_raw) if weight_raw not in (None, "") else 0.0
        if weight <= 0:
            return None

        gender = answers.get("gender")
        if gender not in ("male", "female"):
            return None

        activity = answers.get("activityLevel")
        work_type = _ACTIVITY_TO_WORKTYPE.get(activity) if activity else None
        if work_type is None:
            return None

        goal_raw = answers.get("nutritionGoal")
        goal = _GOAL_MAP.get(goal_raw) if goal_raw else None
        if goal is None:
            return None

        return CalculatorInputs(
            weight=weight,
            gender=gender,
            work_type=work_type,
            goal=goal,
            training_types=_derive_trainings(answers),
        )
    except (TypeError, ValueError):
        return None


def _derive_trainings(answers: dict[str, Any]) -> list[TrainingInput]:
    if answers.get("willExercise") != "yes":
        return []

    sessions = _DAYS_TO_SESSIONS.get(answers.get("exerciseDays") or "")
    if not sessions:
        return []

    exercise_type = answers.get("exerciseType")
    if exercise_type == "gym":
        return [TrainingInput(type="resistance", sessions=sessions)]
    if exercise_type in ("home", "walking"):
        return [
            TrainingInput(
                type="aerobic",
                sessions=sessions,
                time=_AEROBIC_DEFAULT_TIME,
            )
        ]
    if exercise_type == "mixed":
        # Mixed = some resistance + some aerobic. Conservative: count as
        # resistance only (the higher-impact branch), avoiding double-count.
        return [TrainingInput(type="resistance", sessions=sessions)]
    # "not-sure" or missing → skip training contribution
    return []
