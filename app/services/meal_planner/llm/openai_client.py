"""
OpenAI adapter — the concrete `LLMClient` for the meal planner.

Isolates every provider quirk so the rest of the pipeline stays clean:
  • structured output via an internal string-id DTO (avoids UUID/strict-schema
    friction), then coerced to the core `MealProposal`;
  • reasoning models (o1/o3/o4) take a "developer" role instead of "system" and
    reject a custom temperature — handled here;
  • hallucinated non-UUID meal_ids are dropped (the validator then rejects the
    proposal and repair kicks in) rather than crashing the request.
"""

from __future__ import annotations

import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.meal_planner import config
from app.services.meal_planner.llm.base import Message, T
from app.services.meal_planner.schemas import MealProposal, ProposedPick

# Reasoning families: different role vocabulary + no temperature knob.
_REASONING_PREFIXES = ("o1", "o3", "o4")


class _LLMPick(BaseModel):
    meal_id: str
    position: int


class _LLMProposal(BaseModel):
    picks: list[_LLMPick]
    rationale: str


class OpenAIClient:
    """LLMClient backed by OpenAI structured outputs."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(api_key=key)

    async def complete_structured(
        self, messages: list[Message], schema: type[T], *, model: str
    ) -> T:
        reasoning = model.startswith(_REASONING_PREFIXES)
        role_map = {"system": "developer"} if reasoning else {}
        payload = [
            {"role": role_map.get(m.role, m.role), "content": m.content}
            for m in messages
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": payload,
            "response_format": _LLMProposal,
        }
        if not reasoning:
            kwargs["temperature"] = config.TEMPERATURE

        completion = await self._client.beta.chat.completions.parse(**kwargs)
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            # Empty proposal → validator rejects → repair. Never crash the call.
            return MealProposal(picks=[], rationale="")  # type: ignore[return-value]

        picks: list[ProposedPick] = []
        for p in parsed.picks:
            try:
                picks.append(
                    ProposedPick(meal_id=uuid.UUID(p.meal_id), position=p.position)
                )
            except (ValueError, AttributeError):
                continue  # drop non-UUID hallucinations; validator handles the gap

        return MealProposal(  # type: ignore[return-value]
            picks=picks, rationale=parsed.rationale
        )
