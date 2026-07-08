"""
Chat generation job (polling model).

Runs as a background task after the consultant sends a message. Updates the
assistant message's status/step at each stage (committed so the polling client
sees the thinking text), then fills content + sources when done.

  step "מחפש במאגר הידע…"  → retrieve knowledge chunks
  step "קורא נתוני הלקוח…"  → load client context (if scoped)
  step "מנסח תשובה…"        → gpt-4o answer
"""

from __future__ import annotations

import logging
import time
import uuid

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.chat import ChatMessage
from app.services.chat_assistant import prompt as prompter
from app.services.chat_assistant import repository
from app.services.chat_assistant.client_context import load_client_context
from app.services.knowledge_base import retrieval
from app.services.llm_audit import save_llm_request

logger = logging.getLogger(__name__)


async def _set_step(session, msg, step: str, status: str = "generating") -> None:  # type: ignore[no-untyped-def]
    msg.status = status
    msg.step = step
    await session.flush()
    await session.commit()


async def run_chat(assistant_message_id: uuid.UUID, question: str) -> None:
    """Generate the assistant answer for one message. Fire-and-forget safe."""
    async with AsyncSessionLocal() as session:
        msg = await session.get(ChatMessage, assistant_message_id)
        if msg is None:
            return
        conv = await repository.get_conversation(session, msg.conversation_id)
        if conv is None:
            return

        try:
            await _set_step(session, msg, "מחפש במאגר הידע…")
            chunks = await retrieval.search(session, question)

            client_ctx = None
            if conv.client_id is not None:
                await _set_step(session, msg, "קורא נתוני הלקוח…")
                client_ctx = await load_client_context(session, conv.client_id)

            await _set_step(session, msg, "מנסח תשובה…")
            history = await repository.recent_history(session, conv.id, limit=10)
            history = [(r, c) for r, c in history if c]
            # The current question is appended separately by build_messages —
            # drop it from history so it isn't sent twice.
            if history and history[-1] == ("user", question):
                history = history[:-1]
            messages = prompter.build_messages(question, chunks, client_ctx, history)

            answer = await _complete(messages)

            msg.content = answer
            msg.sources = [
                {
                    "document_id": c.document_id,
                    "title": c.title,
                    "similarity": round(c.similarity, 3),
                }
                for c in chunks
            ]
            msg.status = "ready"
            msg.step = None
            if conv.title is None:
                conv.title = question[:80]
            await session.commit()
            logger.info(
                "chat READY msg=%s chunks=%d client=%s",
                assistant_message_id,
                len(chunks),
                conv.client_id,
            )
        except Exception as exc:
            logger.warning("chat FAILED msg=%s: %s", assistant_message_id, exc)
            await session.rollback()
            msg = await session.get(ChatMessage, assistant_message_id)
            if msg is not None:
                msg.status = "failed"
                msg.step = None
                msg.error = str(exc)[:1000]
                await session.commit()


async def _complete(messages: list[dict[str, str]]) -> str:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.OPENAI_CHAT_MODEL
    t0 = time.perf_counter()
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.3,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    usage = getattr(resp, "usage", None)
    try:
        await save_llm_request(
            model=model,
            status="success",
            messages=messages,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            latency_ms=latency_ms,
        )
    except Exception:
        logger.warning("failed to audit chat call", exc_info=True)
    return resp.choices[0].message.content or ""
