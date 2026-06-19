"""Hybrid retriever: BM25 + dense + fusion, with a deterministic record path."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Literal

from aih.llm import get_embedder
from aih.llm.base import Embedder
from aih.rag.corpus import load_chunks
from aih.rag.dense import DenseIndex
from aih.rag.fusion import FusedScore, alpha_fusion, reciprocal_rank_fusion
from aih.rag.models import (
    AuthoritativeRecord,
    Chunk,
    Provenance,
    RetrievedChunk,
    SearchResult,
)
from aih.rag.sparse import BM25Index

FusionMethod = Literal["alpha", "rrf"]

#: A resolver maps a campaign id to its authoritative record (or None).
RecordResolver = Callable[[str], Awaitable[AuthoritativeRecord | None]]

# Campaign ids look like "pa-1", "nr-2", "cb-3".
_CAMPAIGN_ID_RE = re.compile(r"\b([a-z]{2}-\d+)\b", re.IGNORECASE)


class HybridRetriever:
    """Hybrid retrieval over a chunked corpus."""

    def __init__(
        self,
        chunks: list[Chunk] | None = None,
        *,
        embedder: Embedder | None = None,
        record_resolver: RecordResolver | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else load_chunks()
        self.embedder = embedder or get_embedder()
        self._sparse = BM25Index(self.chunks)
        self._dense = DenseIndex(self.chunks, self.embedder)
        self._resolver = record_resolver

    async def search(
        self,
        query: str,
        *,
        k: int = 5,
        alpha: float = 0.5,
        method: FusionMethod = "rrf",
    ) -> SearchResult:
        """Return fused, cited chunks plus an optional authoritative record."""
        deterministic = await self._resolve_deterministic(query)
        chunks = self._retrieve_text(query, k=k, alpha=alpha, method=method)
        return SearchResult(query=query, chunks=chunks, deterministic=deterministic)

    def _retrieve_text(
        self, query: str, *, k: int, alpha: float, method: FusionMethod
    ) -> list[RetrievedChunk]:
        if not self.chunks:
            return []
        sparse = self._sparse.scores(query)
        dense = self._dense.scores(query)
        if method == "alpha":
            fused = alpha_fusion(sparse, dense, alpha=alpha)
        else:
            fused = reciprocal_rank_fusion(sparse, dense)
        ranked = sorted(fused, key=lambda f: f.fused, reverse=True)[:k]
        return [self._to_result(f, method) for f in ranked]

    def _to_result(self, f: FusedScore, method: FusionMethod) -> RetrievedChunk:
        chunk = self.chunks[f.index]
        return RetrievedChunk(
            text=chunk.text,
            score=f.fused,
            metadata=chunk.metadata,
            provenance=Provenance(
                source=f"doc:{chunk.doc_id}",
                doc_id=chunk.doc_id,
                chunk_id=chunk.id,
                bm25=f.sparse,
                dense=f.dense,
                fused=f.fused,
                method=method,
                signals=f.signals,
            ),
        )

    async def _resolve_deterministic(self, query: str) -> AuthoritativeRecord | None:
        if self._resolver is None:
            return None
        match = _CAMPAIGN_ID_RE.search(query)
        if not match:
            return None
        try:
            return await self._resolver(match.group(1).lower())
        except Exception:  # noqa: BLE001 - deterministic path degrades gracefully
            return None
