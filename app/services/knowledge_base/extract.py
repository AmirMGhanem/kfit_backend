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
    "text/html": "html",
    "application/xhtml+xml": "html",
}

# Also accept by extension when the browser sends a vague content-type.
_EXT = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "text",
    ".md": "text",
    ".markdown": "text",
    ".html": "html",
    ".htm": "html",
}


# Canonical content-type for each kind (used when a URL server sends a vague or
# missing content-type but the extension tells us what it is).
CANONICAL_TYPE = {
    "pdf": "application/pdf",
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "html": "text/html",
    "text": "text/plain",
}


def detect_kind(content_type: str, filename: str) -> str | None:
    """The extractor kind for a content-type/filename, or None if unsupported."""
    if content_type in SUPPORTED:
        return SUPPORTED[content_type]
    lower = filename.lower()
    for ext, kind in _EXT.items():
        if lower.endswith(ext):
            return kind
    return None


def extract_text(data: bytes, content_type: str, filename: str) -> str:
    kind = detect_kind(content_type, filename)
    if kind is None:
        raise ValueError(f"unsupported file type: {content_type} ({filename})")

    if kind == "pdf":
        return _extract_pdf(data)
    if kind == "docx":
        return _extract_docx(data)
    if kind == "html":
        return _extract_html(data)
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


def _extract_html(data: bytes) -> str:
    """Main-content text from an HTML page (nav/footer/ads stripped)."""
    import trafilatura

    html = data.decode("utf-8", errors="replace")
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if text and text.strip():
        return text.strip()
    # Fallback: strip tags with the stdlib parser (crude but dependency-free).
    return _strip_tags(html)


def _strip_tags(html: str) -> str:
    from html.parser import HTMLParser

    class _Text(HTMLParser):
        _SKIP = {"script", "style", "noscript", "head", "svg"}

        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self._skip = 0

        def handle_starttag(self, tag: str, attrs: object) -> None:
            if tag in self._SKIP:
                self._skip += 1

        def handle_endtag(self, tag: str) -> None:
            if tag in self._SKIP and self._skip:
                self._skip -= 1

        def handle_data(self, data: str) -> None:
            if not self._skip and data.strip():
                self.parts.append(data.strip())

    parser = _Text()
    parser.feed(html)
    return "\n".join(parser.parts)
