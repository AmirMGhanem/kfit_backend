"""
The LLM boundary — one small Protocol the pipeline depends on.

Wiring a real provider (OpenAI) later means writing ONE class that implements
`complete_structured`; nothing else in the pipeline changes. The steps only ever
see `LLMClient`, never a concrete SDK.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Message(BaseModel):
    """A single chat message. role ∈ {system, user, assistant}."""

    role: str
    content: str


class LLMClient(Protocol):
    """
    Minimal structured-output contract.

    `complete_structured` sends the messages against `model` and returns an
    instance of `schema`, already validated. `model` is per-call (as with the
    provider APIs) so the pipeline can use a fast builder model and a stronger
    repair model through one client. The implementation is responsible for
    asking the provider for JSON/tool output and parsing it into `schema`
    (retrying on malformed output is the provider adapter's concern).
    """

    async def complete_structured(
        self, messages: list[Message], schema: type[T], *, model: str
    ) -> T: ...
