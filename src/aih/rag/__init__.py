"""Hybrid retrieval (RAG): BM25 + dense + fusion (alpha & RRF).

See ``specs/rag.md``.
"""

from __future__ import annotations

from aih.rag.models import (
    AuthoritativeRecord,
    Chunk,
    Provenance,
    RetrievedChunk,
    SearchResult,
)
from aih.rag.retriever import HybridRetriever, RecordResolver

__all__ = [
    "AuthoritativeRecord",
    "Chunk",
    "HybridRetriever",
    "Provenance",
    "RecordResolver",
    "RetrievedChunk",
    "SearchResult",
]
