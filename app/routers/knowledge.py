"""
Knowledge-base routes.

  POST   /knowledge            upload a file (admin) → MinIO + async ingestion
  GET    /knowledge            list documents (staff)
  DELETE /knowledge/{id}       delete a document + its chunks + MinIO object (admin)
  POST   /knowledge/{id}/reindex   re-run ingestion (admin)

Upload stores the raw file in MinIO, creates the document row (status=pending),
and fires the ingestion pipeline as a background task — the request returns
immediately.
"""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import get_session
from app.core.deps import require_admin, require_staff
from app.models.user import User
from app.services.knowledge_base import repository, run_ingestion
from app.services.knowledge_base.web_fetch import FetchError, fetch_url

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

MAX_SIZE = 20 * 1024 * 1024  # 20 MB (matches nginx client_max_body_size)


class DocumentOut(BaseModel):
    id: str
    title: str
    filename: str
    content_type: str
    size_bytes: int
    category: str | None
    source_url: str | None
    status: str
    error: str | None
    chunk_count: int
    created_at: str


class UrlIn(BaseModel):
    url: str
    title: str | None = None
    category: str | None = None


def _out(d) -> DocumentOut:  # type: ignore[no-untyped-def]
    return DocumentOut(
        id=str(d.id),
        title=d.title,
        filename=d.filename,
        content_type=d.content_type,
        size_bytes=d.size_bytes,
        category=d.category,
        source_url=d.source_url,
        status=d.status,
        error=d.error,
        chunk_count=d.chunk_count,
        created_at=d.created_at.isoformat(),
    )


@router.post("/", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str | None = Form(None),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "file too large (max 20 MB)")

    content_type = file.content_type or "application/octet-stream"
    key = f"knowledge/{uuid.uuid4()}-{file.filename}"
    storage.put_object(key, data, content_type)

    doc = await repository.create_document(
        session,
        title=title,
        filename=file.filename or "untitled",
        minio_key=key,
        content_type=content_type,
        size_bytes=len(data),
        category=category,
        uploaded_by=user.id,
    )
    await session.commit()

    background_tasks.add_task(run_ingestion, doc.id)
    return _out(doc)


_TYPE_EXT = {
    "text/html": "html",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


def _filename_from_url(url: str, content_type: str) -> str:
    from urllib.parse import urlparse

    p = urlparse(url)
    name = (p.netloc + p.path).strip("/") or p.netloc or "page"
    ext = _TYPE_EXT.get(content_type)
    if ext and not name.lower().endswith(f".{ext}"):
        name = f"{name}.{ext}"
    return name[:200]


@router.post("/url", response_model=DocumentOut, status_code=201)
async def ingest_url(
    body: UrlIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    """Fetch a URL (HTML page or direct PDF/DOCX/text) and ingest it like an upload."""
    try:
        page = await fetch_url(body.url)
    except FetchError as exc:
        raise HTTPException(400, str(exc)) from exc

    ext = _TYPE_EXT.get(page.content_type, "bin")
    key = f"knowledge/{uuid.uuid4()}.{ext}"
    storage.put_object(key, page.data, page.content_type)

    filename = _filename_from_url(page.final_url, page.content_type)
    title = (body.title or "").strip() or page.title or filename
    doc = await repository.create_document(
        session,
        title=title,
        filename=filename,
        minio_key=key,
        content_type=page.content_type,
        size_bytes=len(page.data),
        category=(body.category or None),
        uploaded_by=user.id,
        source_url=page.final_url,
    )
    await session.commit()

    background_tasks.add_task(run_ingestion, doc.id)
    return _out(doc)


@router.get("/", dependencies=[Depends(require_staff)])
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> list[DocumentOut]:
    docs = await repository.list_documents(session)
    return [_out(d) for d in docs]


@router.delete("/{document_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    doc = await repository.get_document(session, document_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    key = doc.minio_key
    await session.delete(doc)  # cascades to chunks
    await session.commit()
    storage.delete_object(key)


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentOut,
    dependencies=[Depends(require_admin)],
)
async def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    doc = await repository.get_document(session, document_id)
    if doc is None:
        raise HTTPException(404, "document not found")

    # For a web-sourced document, re-fetch the page so reindex picks up changes.
    if doc.source_url:
        try:
            page = await fetch_url(doc.source_url)
        except FetchError as exc:
            raise HTTPException(400, str(exc)) from exc
        storage.put_object(doc.minio_key, page.data, page.content_type)
        doc.content_type = page.content_type
        doc.size_bytes = len(page.data)

    await repository.set_status(session, doc, "pending", error=None)
    await session.commit()
    background_tasks.add_task(run_ingestion, doc.id)
    return _out(doc)
