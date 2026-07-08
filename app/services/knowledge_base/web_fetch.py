"""
Fetch a document from a URL for knowledge-base ingestion.

Downloads over HTTP(S) with redirects, a bounded timeout and size cap, and a
light SSRF guard (no localhost / private-network / non-HTTP targets). The URL may
point at an HTML page OR a direct file (PDF, DOCX, text) — whatever the extractor
supports; the raw bytes are handed to the same ingestion pipeline as an uploaded
file, so retrieval, chunking and embedding stay identical across sources.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.services.knowledge_base.extract import CANONICAL_TYPE, detect_kind

# Matches uploads: 20 MB ceiling on the fetched body.
MAX_BYTES = 20 * 1024 * 1024
TIMEOUT_S = 20.0
# A real UA — some sites 403 the default httpx agent.
_UA = (
    "Mozilla/5.0 (compatible; KfitKnowledgeBot/1.0; +https://kfit)"
    " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FetchError(ValueError):
    """The URL could not be fetched into usable HTML (bad scheme, host, type…)."""


@dataclass
class FetchedPage:
    data: bytes
    content_type: str  # canonical type for the extractor (text/html, application/pdf…)
    final_url: str
    title: str | None  # page <title> for HTML, else None


def _guard_host(url: str) -> str:
    """Reject non-HTTP schemes and obvious internal targets (basic SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("only http(s) URLs are supported")
    host = parsed.hostname
    if not host:
        raise FetchError("URL has no host")
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".local"):
        raise FetchError("refusing to fetch a local address")
    # Block raw private / loopback / link-local IP literals.
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise FetchError("refusing to fetch a private address")
    except ValueError:
        pass  # hostname, not an IP literal — fine
    return host


def _extract_title(html: bytes) -> str | None:
    m = _TITLE_RE.search(html.decode("utf-8", errors="replace"))
    if not m:
        return None
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return title[:300] or None


async def fetch_url(url: str) -> FetchedPage:
    """Fetch a URL (HTML page or direct file). Raises FetchError on any problem."""
    url = url.strip()
    _guard_host(url)

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=TIMEOUT_S,
            headers={"User-Agent": _UA, "Accept": "*/*"},
            max_redirects=5,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise FetchError(f"could not fetch URL: {exc}") from exc

    if resp.status_code >= 400:
        raise FetchError(f"URL returned HTTP {resp.status_code}")

    # Redirects can escape the guard — re-check the final host.
    final_url = str(resp.url)
    _guard_host(final_url)

    body = resp.content
    if not body:
        raise FetchError("URL returned an empty body")
    if len(body) > MAX_BYTES:
        raise FetchError("document too large (max 20 MB)")

    # Decide the extractor kind from the server's content-type, falling back to
    # the URL's file extension (servers often send octet-stream for PDFs).
    header_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    path = urlparse(final_url).path
    kind = detect_kind(header_type, path)
    if kind is None:
        raise FetchError(
            f"unsupported document type at URL (content-type: {header_type or 'unknown'})"
        )

    content_type = CANONICAL_TYPE[kind]
    title = _extract_title(body) if kind == "html" else None
    return FetchedPage(
        data=body,
        content_type=content_type,
        final_url=final_url,
        title=title,
    )
