"""
Token-based chunking for RAG.

Splits extracted text into overlapping windows sized by tokens (not characters),
so each chunk fits the embedding model and retrieval stays coherent. Prefers
paragraph boundaries, falling back to a hard token window for very long blocks.
"""

from __future__ import annotations

import tiktoken

CHUNK_TOKENS = 800
OVERLAP_TOKENS = 100
_ENC = tiktoken.get_encoding("cl100k_base")


def _tok(text: str) -> list[int]:
    return _ENC.encode(text)


def count_tokens(text: str) -> int:
    return len(_tok(text))


def chunk_text(text: str) -> list[str]:
    """Return a list of ~CHUNK_TOKENS chunks with OVERLAP_TOKENS overlap."""
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    for para in paragraphs:
        pt = count_tokens(para)
        if pt > CHUNK_TOKENS:
            # Flush current buffer, then hard-split the oversized paragraph.
            if buf:
                chunks.append("\n\n".join(buf))
                buf, buf_tokens = [], 0
            chunks.extend(_hard_split(para))
            continue
        if buf_tokens + pt > CHUNK_TOKENS and buf:
            chunks.append("\n\n".join(buf))
            # Start next buffer with a tail overlap for context continuity.
            buf, buf_tokens = _overlap_tail(buf)
        buf.append(para)
        buf_tokens += pt

    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def _hard_split(text: str) -> list[str]:
    toks = _tok(text)
    out: list[str] = []
    step = CHUNK_TOKENS - OVERLAP_TOKENS
    for i in range(0, len(toks), step):
        window = toks[i : i + CHUNK_TOKENS]
        out.append(_ENC.decode(window))
        if i + CHUNK_TOKENS >= len(toks):
            break
    return out


def _overlap_tail(buf: list[str]) -> tuple[list[str], int]:
    """Keep trailing paragraphs up to ~OVERLAP_TOKENS as the next buffer's head."""
    tail: list[str] = []
    total = 0
    for para in reversed(buf):
        pt = count_tokens(para)
        if total + pt > OVERLAP_TOKENS and tail:
            break
        tail.insert(0, para)
        total += pt
    return tail, total
