"""
Submission analyzer — one gpt-4o call that turns an onboarding submission into
welcome-call notes (red flags / pain points / insights), persisted for the
consultant.

Runs asynchronously (fired as a background task after the client submits) with
its own DB session, so it never blocks or rolls back the submission. Best-effort:
any failure is captured as a ``failed`` insight row, never raised to the caller.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.llm_audit import save_llm_request
from app.services.submission_analyzer import repository
from app.services.submission_analyzer.prompt import build_messages
from app.services.submission_analyzer.schemas import SubmissionAnalysis

logger = logging.getLogger(__name__)


async def run_analysis(submission_id: uuid.UUID, *, model: str | None = None) -> None:
    """Analyze a submission and persist the insight. Safe to fire-and-forget."""
    model = model or settings.OPENAI_ANALYZER_MODEL
    async with AsyncSessionLocal() as session:
        submission = await repository.fetch_submission(session, submission_id)
        if submission is None or submission.client_id is None:
            logger.warning("analyzer: submission %s missing/clientless", submission_id)
            return

        messages = build_messages(submission.payload)
        try:
            analysis = await _call(messages, model, submission_id)
            await repository.save_ready(session, submission, analysis, model)
            logger.info(
                "submission analysis READY submission=%s flags=%d pains=%d insights=%d",
                submission_id,
                len(analysis.red_flags),
                len(analysis.pain_points),
                len(analysis.insights),
            )
        except Exception as exc:  # never let a background task escape
            logger.warning(
                "submission analysis FAILED submission=%s: %s", submission_id, exc
            )
            await repository.save_failed(session, submission, model, str(exc)[:1000])
        await session.commit()


async def _call(
    messages: list[dict[str, str]], model: str, submission_id: uuid.UUID
) -> SubmissionAnalysis:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    logger.info("analyzer LLM call → model=%s submission=%s", model, submission_id)
    t0 = time.perf_counter()
    try:
        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            response_format=SubmissionAnalysis,
            temperature=0.3,
        )
    except Exception as exc:
        await _audit(
            model,
            messages,
            submission_id,
            "error",
            int((time.perf_counter() - t0) * 1000),
            error=str(exc)[:1000],
        )
        raise

    latency_ms = int((time.perf_counter() - t0) * 1000)
    choice = completion.choices[0]
    parsed = choice.message.parsed
    await _audit(
        model,
        messages,
        submission_id,
        "success",
        latency_ms,
        response=parsed.model_dump() if parsed else None,
        usage=getattr(completion, "usage", None),
        finish_reason=choice.finish_reason,
    )
    if parsed is None:
        raise RuntimeError("analyzer: model returned no parsed content")
    return parsed


async def _audit(
    model: str,
    messages: list[dict[str, str]],
    submission_id: uuid.UUID,
    status: str,
    latency_ms: int,
    *,
    response: dict[str, Any] | None = None,
    usage: object | None = None,
    finish_reason: str | None = None,
    error: str | None = None,
) -> None:
    try:
        await save_llm_request(
            submission_id=submission_id,
            model=model,
            status=status,
            messages=messages,
            response=response,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            error=error,
        )
    except Exception:
        logger.warning("failed to persist analyzer llm_request", exc_info=True)
