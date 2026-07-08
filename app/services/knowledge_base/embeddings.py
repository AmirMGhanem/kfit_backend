"""
OpenAI embeddings for the knowledge base.

Turns text into 1536-dim vectors (text-embedding-3-small). Used both at ingestion
(embed each chunk) and at query time (embed the question). Best-effort audit to
llm_requests.
"""

from __future__ import annotations

import logging
import time

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm_audit import save_llm_request

logger = logging.getLogger(__name__)


def _client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts; returns one vector per input, in order."""
    if not texts:
        return []
    model = settings.OPENAI_EMBEDDING_MODEL
    t0 = time.perf_counter()
    resp = await _client().embeddings.create(model=model, input=texts)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    usage = getattr(resp, "usage", None)
    try:
        await save_llm_request(
            model=model,
            status="success",
            messages=[{"role": "system", "content": f"embed {len(texts)} texts"}],
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            latency_ms=latency_ms,
        )
    except Exception:
        logger.warning("failed to audit embedding call", exc_info=True)

    return [d.embedding for d in resp.data]


async def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    vectors = await embed_texts([text])
    return vectors[0]
