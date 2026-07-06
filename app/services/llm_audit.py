"""
Shared LLM-call audit sink.

Writes one ``llm_requests`` row in its own short-lived transaction so audit
logging is committed independently of — and never rolls back — the work that
made the call. Best-effort: callers swallow exceptions.
"""

from __future__ import annotations

from typing import Any

from app.core.database import AsyncSessionLocal
from app.models.llm_request import LLMRequest


async def save_llm_request(**fields: Any) -> None:
    async with AsyncSessionLocal() as session:
        session.add(LLMRequest(**fields))
        await session.commit()
