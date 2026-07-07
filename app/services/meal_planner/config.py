"""
Meal-planner tunables. Kept separate from secrets — the API key lives in
`app.core.config.settings.OPENAI_API_KEY`; this file is behavioural knobs only.
"""

from __future__ import annotations

from app.core.config import settings

# How many times to ask the LLM to fix an invalid proposal before giving up.
MAX_REPAIR_ATTEMPTS: int = 3

# Two-model split (env-overridable via settings):
#   BUILDER — fast model for the first proposal (the common path).
#   REPAIR  — stronger reasoning model, only runs when validation rejects a
#             proposal (rare). Reasoning helps the "make it fit the window" fix.
BUILDER_MODEL: str = settings.OPENAI_BUILDER_MODEL
REPAIR_MODEL: str = settings.OPENAI_REPAIR_MODEL

# Determinism for the builder: meal selection should be near-deterministic, not
# creative. (Reasoning repair models may ignore temperature — the adapter's
# concern, not this file's.)
TEMPERATURE: float = 0.2

# ── Nutrition rules (K.FIT operator rules) ──────────────────────────────────
# Which figure from the calculation window is "daily calories" for the 10%.
DAILY_CALORIES_BASIS: str = "midpoint"  # midpoint | min | max

# R1 — free calories = this fraction of daily, rounded to the nearest bucket.
FREE_CALORIE_FRACTION: float = 0.10
FREE_CALORIE_BUCKETS: tuple[int, ...] = (120, 150, 200, 250)

# R2 — the two main meals split the remaining calories small : big = 1/3 : 2/3.
MEAL_SPLIT: tuple[float, float] = (1 / 3, 2 / 3)

# R2 — allowed per-meal calorie deviation: min(50 kcal, 3% of daily calories).
TOLERANCE_ABS: int = 50
TOLERANCE_PCT: float = 0.03

# R4 — protein tiebreaker: within this calorie gap, prefer the option that adds
# at least this many grams of protein.
TIEBREAK_CALORIE_GAP: int = 50
TIEBREAK_MIN_PROTEIN_GRAMS: int = 5

# R7 — protein-source qualification minimums (grams) for snacks.
SNACK_PROTEIN_BAR_MIN_G: int = 10
SNACK_PROTEIN_DRINK_MIN_G: int = 15
