"""
Ingestion pipeline: MinIO file -> text -> chunks -> embeddings -> pgvector.

Runs asynchronously (fired as a background task after upload) with its own DB
session, so it never blocks or rolls back the upload request. Status machine:
pending -> processing -> ready | failed.
"""

from __future__ import annotations

import logging
import uuid

from app.core import storage
from app.core.database import AsyncSessionLocal
from app.services.knowledge_base import repository
from app.services.knowledge_base.chunking import chunk_text, count_tokens
from app.services.knowledge_base.embeddings import embed_texts
from app.services.knowledge_base.extract import extract_text

logger = logging.getLogger(__name__)

# Embed in batches so a big document doesn't hit request limits.
EMBED_BATCH = 64


async def run_ingestion(document_id: uuid.UUID) -> None:
    """Process one uploaded document. Safe to fire-and-forget."""
    async with AsyncSessionLocal() as session:
        doc = await repository.get_document(session, document_id)
        if doc is None:
            logger.warning("ingestion: document %s not found", document_id)
            return
        await repository.set_status(session, doc, "processing")
        await session.commit()

        try:
            data = storage.get_object(doc.minio_key)
            text = extract_text(data, doc.content_type, doc.filename)
            if not text.strip():
                raise ValueError("no extractable text in file")

            chunks = chunk_text(text)
            logger.info(
                "ingestion: doc=%s chars=%d chunks=%d",
                document_id,
                len(text),
                len(chunks),
            )

            rows: list[tuple[int, str, int, list[float]]] = []
            for start in range(0, len(chunks), EMBED_BATCH):
                batch = chunks[start : start + EMBED_BATCH]
                vectors = await embed_texts(batch)
                for i, (content, vec) in enumerate(zip(batch, vectors)):
                    rows.append((start + i, content, count_tokens(content), vec))

            await repository.replace_chunks(session, document_id, rows)
            await repository.set_status(session, doc, "ready", chunk_count=len(rows))
            await session.commit()
            logger.info("ingestion READY doc=%s chunks=%d", document_id, len(rows))
        except Exception as exc:
            logger.warning("ingestion FAILED doc=%s: %s", document_id, exc)
            await session.rollback()
            doc = await repository.get_document(session, document_id)
            if doc is not None:
                await repository.set_status(
                    session, doc, "failed", error=str(exc)[:1000]
                )
                await session.commit()
