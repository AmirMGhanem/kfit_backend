"""
Retrieval: embed a question and pull the most similar knowledge chunks.

Uses pgvector cosine distance (`<=>`) with the HNSW index, joined to the parent
document for citation titles. Returns only chunks above a similarity floor so the
prompt isn't padded with irrelevant text.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_base.embeddings import embed_query

TOP_K = 6
# Low floor: cross-lingual matches (e.g. Hebrew query vs English doc) score lower
# than same-language ones. Top-k ranking + the LLM's grounding instruction ("say
# so if it isn't in the material") do the real relevance filtering.
MIN_SIMILARITY = 0.1


@dataclass
class RetrievedChunk:
    document_id: str
    title: str
    content: str
    similarity: float


async def search(
    session: AsyncSession,
    query: str,
    *,
    top_k: int = TOP_K,
    min_similarity: float = MIN_SIMILARITY,
) -> list[RetrievedChunk]:
    vec = await embed_query(query)
    rows = (
        await session.execute(
            text(
                "SELECT c.document_id, d.title, c.content, "
                "1 - (c.embedding <=> :v) AS similarity "
                "FROM knowledge_chunks c "
                "JOIN knowledge_documents d ON d.id = c.document_id "
                "WHERE d.status = 'ready' "
                "ORDER BY c.embedding <=> :v "
                "LIMIT :k"
            ),
            {"v": str(vec), "k": top_k},
        )
    ).all()
    return [
        RetrievedChunk(
            document_id=str(r.document_id),
            title=r.title,
            content=r.content,
            similarity=float(r.similarity),
        )
        for r in rows
        if float(r.similarity) >= min_similarity
    ]
