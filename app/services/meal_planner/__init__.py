"""
Meal-planner agent: selects catalog meals to fit a client's calorie window.

Public surface:
    run_pipeline  — orchestrate one generation run
    PlanOutcome   — the result type
    LLMClient     — the boundary to implement when wiring a real model
"""

from app.services.meal_planner.llm.base import LLMClient
from app.services.meal_planner.pipeline import run_pipeline
from app.services.meal_planner.schemas import PlanOutcome

__all__ = ["run_pipeline", "PlanOutcome", "LLMClient"]
