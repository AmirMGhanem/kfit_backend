"""
Step 01 — Build context (deterministic, no LLM).

Gathers everything the agent needs into a single PlanContext:
  • the calorie window + request params (from the calculation)
  • the active meal catalog

No prompt here — this step only queries the database.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.meal_planner import repository
from app.services.meal_planner.schemas import PlanContext


async def build_context(
    session: AsyncSession,
    calculation_id: uuid.UUID,
    *,
    meals_count: int,
    include_snack: bool,
) -> PlanContext:
    client_id, targets = await repository.fetch_targets(
        session,
        calculation_id,
        meals_count=meals_count,
        include_snack=include_snack,
    )
    candidates = await repository.fetch_active_catalog(session)
    return PlanContext(
        client_id=client_id,
        calculation_id=calculation_id,
        targets=targets,
        candidates=candidates,
    )
