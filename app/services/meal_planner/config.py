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
