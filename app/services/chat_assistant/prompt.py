"""
Prompt assembly for the consultant chat assistant.

System rules + retrieved knowledge (cited) + client context (if scoped) + recent
history + the question. Grounding is strict: answer from the provided material;
if it isn't there, say so.
"""

from __future__ import annotations

from app.services.knowledge_base.retrieval import RetrievedChunk

SYSTEM_PROMPT = """\
You are the K.FIT assistant for nutrition consultants. You help the consultant
with questions about nutrition, the K.FIT method, and their specific clients.

Grounding rules:
- Answer PRIMARILY from the KNOWLEDGE BASE excerpts and the CLIENT CONTEXT
  provided below. Do not invent facts.
- If the answer is not in the provided material, say so plainly (in Hebrew) and,
  if useful, suggest what to check — do NOT fabricate.
- When you use a knowledge excerpt, cite it by its [source: title].
- For clinical/medical matters, do not diagnose or prescribe — advise confirming
  with a doctor.

Style:
- Answer in HEBREW.
- The consultant may be a man or a woman — use GENDER-NEUTRAL phrasing for the
  consultant (impersonal/infinitive: "כדאי…", "מומלץ…", "יש ל…"). The client is
  referred to with their own known gender.
- Be concise, practical, and specific to what was asked.
"""


def _format_knowledge(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no relevant knowledge-base excerpts found)"
    parts = []
    for c in chunks:
        parts.append(f"[source: {c.title}]\n{c.content}")
    return "\n\n".join(parts)


def build_messages(
    question: str,
    chunks: list[RetrievedChunk],
    client_context: str | None,
    history: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """history: list of (role, content) for the last few turns (chronological)."""
    context_block = "=== KNOWLEDGE BASE ===\n" + _format_knowledge(chunks)
    if client_context:
        context_block += "\n\n" + client_context

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context_block},
    ]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages
