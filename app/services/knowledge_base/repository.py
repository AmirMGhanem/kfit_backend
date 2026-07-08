"""Database access for the knowledge base."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


async def create_document(
    session: AsyncSession,
    *,
    title: str,
    filename: str,
    minio_key: str,
    content_type: str,
    size_bytes: int,
    category: str | None,
    uploaded_by: uuid.UUID | None,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        title=title,
        filename=filename,
        minio_key=minio_key,
        content_type=content_type,
        size_bytes=size_bytes,
        category=category,
        uploaded_by=uploaded_by,
        status="pending",
    )
    session.add(doc)
    await session.flush()
    return doc


async def get_document(
    session: AsyncSession, document_id: uuid.UUID
) -> KnowledgeDocument | None:
    return await session.get(KnowledgeDocument, document_id)


async def set_status(
    session: AsyncSession,
    doc: KnowledgeDocument,
    status: str,
    *,
    error: str | None = None,
    chunk_count: int | None = None,
) -> None:
    doc.status = status
    doc.error = error
    if chunk_count is not None:
        doc.chunk_count = chunk_count
    await session.flush()


async def replace_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
    rows: list[tuple[int, str, int, list[float]]],
) -> None:
    """Wipe existing chunks for the doc and insert the new set (idempotent)."""
    await session.execute(
        delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
    )
    for idx, content, tokens, embedding in rows:
        session.add(
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=idx,
                content=content,
                token_count=tokens,
                embedding=embedding,
            )
        )
    await session.flush()


async def list_documents(session: AsyncSession) -> list[KnowledgeDocument]:
    return list(
        (
            await session.execute(
                select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
            )
        ).scalars()
    )
