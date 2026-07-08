"""
Extract plain text from an uploaded knowledge file.

Supports PDF, DOCX, and plain text / markdown. Raises ValueError for unsupported
types so the caller can mark the document failed with a clear reason.
"""

from __future__ import annotations

import io

SUPPORTED = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "text",
    "text/markdown": "text",
}

# Also accept by extension when the browser sends a vague content-type.
_EXT = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "text",
    ".md": "text",
    ".markdown": "text",
}


def _kind(content_type: str, filename: str) -> str | None:
    if content_type in SUPPORTED:
        return SUPPORTED[content_type]
    lower = filename.lower()
    for ext, kind in _EXT.items():
        if lower.endswith(ext):
            return kind
    return None


def extract_text(data: bytes, content_type: str, filename: str) -> str:
    kind = _kind(content_type, filename)
    if kind is None:
        raise ValueError(f"unsupported file type: {content_type} ({filename})")

    if kind == "pdf":
        return _extract_pdf(data)
    if kind == "docx":
        return _extract_docx(data)
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(p.strip() for p in parts if p.strip())


def _extract_docx(data: bytes) -> str:
    import docx  # python-docx

    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())
