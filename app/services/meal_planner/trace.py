"""
Per-generation trace context.

The pipeline sets ``calculation_id`` at the start of a run; the LLM adapter reads
it (best-effort) so each persisted ``llm_requests`` row can be grouped by the
generation it belongs to — without threading the id through the LLMClient
interface. ContextVars are task-local, so concurrent generations don't collide.
"""

from __future__ import annotations

import contextvars

calculation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "meal_planner_calculation_id", default=None
)
