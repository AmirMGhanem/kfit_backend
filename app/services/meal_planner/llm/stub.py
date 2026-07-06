"""
Stand-in LLM clients for the un-wired phase.

- NotWiredLLMClient: the default. Raises a clear error the moment the pipeline
  tries to call the model, pointing at where to implement the real adapter.
- FixtureLLMClient: returns a canned proposal, so the full pipeline (context →
  validate → persist) can be exercised in tests without any API key.

The real OpenAI adapter will live next to this file as `openai_client.py` and
implement the same `LLMClient` Protocol.
"""

from __future__ import annotations

from app.services.meal_planner.llm.base import LLMClient, Message, T
from app.services.meal_planner.schemas import MealProposal


class NotWiredLLMClient:
    """Default client. Fails loudly instead of silently doing nothing."""

    async def complete_structured(
        self, messages: list[Message], schema: type[T], *, model: str
    ) -> T:
        raise RuntimeError(
            f"Meal-planner LLM is not wired yet (requested model={model!r}). "
            "Implement an LLMClient (e.g. "
            "app/services/meal_planner/llm/openai_client.py) and inject it "
            "into run_pipeline(..., llm=...)."
        )


class FixtureLLMClient:
    """
    Returns a preset MealProposal regardless of input. For tests / local runs.

    Example:
        llm = FixtureLLMClient(MealProposal(picks=[...]))
    """

    def __init__(self, proposal: MealProposal) -> None:
        self._proposal = proposal

    async def complete_structured(
        self, messages: list[Message], schema: type[T], *, model: str
    ) -> T:
        # In fixture mode we only ever produce MealProposal; model is ignored.
        return self._proposal  # type: ignore[return-value]


# Type-checker sanity: both satisfy the Protocol.
_not_wired: LLMClient = NotWiredLLMClient()
