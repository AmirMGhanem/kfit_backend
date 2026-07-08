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

import json
import logging
import time
import uuid
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.chat import ChatMessage
from app.services import ai_toolkit
from app.services.chat_assistant import prompt as prompter
from app.services.chat_assistant import repository
from app.services.chat_assistant.client_context import load_client_context
from app.services.knowledge_base import retrieval
from app.services.llm_audit import save_llm_request

logger = logging.getLogger(__name__)

# Cap the tool-calling loop so a misbehaving model can't spin forever.
MAX_TOOL_ITERATIONS = 5


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

            async def _on_data_step() -> None:
                await _set_step(session, msg, "בודק נתונים…")

            scoped = str(conv.client_id) if conv.client_id else None
            answer = await _run_tool_loop(session, messages, _on_data_step, scoped)

            msg.content = answer
            # One source per DOCUMENT (not per chunk) — keep the best similarity.
            by_doc: dict[str, dict[str, Any]] = {}
            for c in chunks:
                cur = by_doc.get(c.document_id)
                if cur is None or c.similarity > cur["similarity"]:
                    by_doc[c.document_id] = {
                        "document_id": c.document_id,
                        "title": c.title,
                        "similarity": round(c.similarity, 3),
                    }
            msg.sources = sorted(
                by_doc.values(), key=lambda s: s["similarity"], reverse=True
            )
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


async def _run_tool_loop(session, messages, on_data_step, scoped_client_id=None) -> str:  # type: ignore[no-untyped-def]
    """
    Drive the chat with function-calling: the model may call read-only toolkit
    fetches, we run them and feed results back, until it returns a final answer.
    Bounded by MAX_TOOL_ITERATIONS; the final pass runs without tools to force an
    answer if the cap is hit.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.OPENAI_CHAT_MODEL
    tools = ai_toolkit.openai_tools()

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = await _chat(client, model, messages, tools=tools)
        m = resp.choices[0].message
        if not m.tool_calls:
            return m.content or ""

        await on_data_step()
        messages.append(
            {
                "role": "assistant",
                "content": m.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in m.tool_calls
                ],
            }
        )
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = await ai_toolkit.execute(
                    tc.function.name, args, session, scoped_client_id
                )
            except Exception as exc:  # tool failure → model recovers
                result = {"error": str(exc)[:300]}
            logger.info("chat tool %s(%s)", tc.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    # Cap hit — one final answer with no tools.
    resp = await _chat(client, model, messages, tools=None)
    return resp.choices[0].message.content or ""


async def _chat(client, model, messages, *, tools) -> Any:  # type: ignore[no-untyped-def]
    t0 = time.perf_counter()
    kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3}
    if tools:
        kwargs["tools"] = tools
    resp = await client.chat.completions.create(**kwargs)
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
    return resp
