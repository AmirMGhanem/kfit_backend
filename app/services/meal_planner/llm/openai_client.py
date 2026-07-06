"""
OpenAI adapter — the concrete `LLMClient` for the meal planner.

Isolates every provider quirk so the rest of the pipeline stays clean:
  • structured output via an internal string-id DTO (avoids UUID/strict-schema
    friction), then coerced to the core `MealProposal`;
  • reasoning models (o1/o3/o4) take a "developer" role instead of "system" and
    reject a custom temperature — handled here;
  • hallucinated non-UUID meal_ids are dropped (the validator then rejects the
    proposal and repair kicks in) rather than crashing the request.

Emits INFO logs of every call + the raw model output so a generation can be
watched in real time (`docker compose logs -f backend`).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.meal_planner import config
from app.services.meal_planner.llm.base import Message, T
from app.services.meal_planner.schemas import MealProposal, ProposedPick

logger = logging.getLogger(__name__)

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

        logger.info("LLM call → model=%s messages=%d", model, len(payload))
        t0 = time.perf_counter()
        completion = await self._client.beta.chat.completions.parse(**kwargs)
        dt = time.perf_counter() - t0

        choice = completion.choices[0]
        usage = getattr(completion, "usage", None)
        if usage is not None:
            logger.info(
                "LLM usage model=%s prompt=%s completion=%s total=%s",
                model,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )

        refusal = getattr(choice.message, "refusal", None)
        if refusal:
            logger.warning("LLM refusal model=%s: %s", model, refusal)

        parsed = choice.message.parsed
        if parsed is None:
            logger.warning(
                "LLM returned no parsed content model=%s finish=%s (%.2fs)",
                model,
                choice.finish_reason,
                dt,
            )
            return MealProposal(picks=[], rationale="")  # type: ignore[return-value]

        raw = [(p.meal_id, p.position) for p in parsed.picks]
        logger.info(
            "LLM returned %d pick(s) model=%s (%.2fs): %s",
            len(parsed.picks),
            model,
            dt,
            raw,
        )

        picks: list[ProposedPick] = []
        dropped: list[str] = []
        for p in parsed.picks:
            try:
                picks.append(
                    ProposedPick(meal_id=uuid.UUID(p.meal_id), position=p.position)
                )
            except (ValueError, AttributeError):
                dropped.append(p.meal_id)

        if dropped:
            logger.warning(
                "dropped %d non-UUID meal_id(s) from LLM: %s", len(dropped), dropped
            )
        logger.info(
            "valid picks=%d rationale=%r", len(picks), (parsed.rationale or "")[:160]
        )

        return MealProposal(  # type: ignore[return-value]
            picks=picks, rationale=parsed.rationale
        )
