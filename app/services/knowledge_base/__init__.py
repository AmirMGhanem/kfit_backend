"""RAG knowledge base — ingestion (Phase 1) and retrieval (Phase 2)."""

from app.services.knowledge_base.ingestion import run_ingestion

__all__ = ["run_ingestion"]
