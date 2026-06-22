"""Hybrid retriever: BM25 + vector dense + fusion + rerank + safety."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Literal

from aih.config import get_settings
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
from aih.rag.query import decompose_query, rewrite_query
from aih.rag.rerank import Reranker, get_reranker
from aih.rag.safety import detect_injection, sanitize_query
from aih.rag.sparse import BM25Index
from aih.rag.vector_store import VectorStore, get_vector_store

FusionMethod = Literal["alpha", "rrf"]
RecordResolver = Callable[[str], Awaitable[AuthoritativeRecord | None]]
_CAMPAIGN_ID_RE = re.compile(r"\b([a-z]{2}-\d+)\b", re.IGNORECASE)


def _confidence_from_chunks(chunks: list[RetrievedChunk]) -> Literal["high", "medium", "low"]:
    if not chunks:
        return "low"
    top = chunks[0].score
    if top >= 0.45:
        return "high"
    if top >= 0.15:
        return "medium"
    return "low"


class HybridRetriever:
    """Hybrid retrieval over a chunked corpus with modern RAG stages."""

    def __init__(
        self,
        chunks: list[Chunk] | None = None,
        *,
        embedder: Embedder | None = None,
        record_resolver: RecordResolver | None = None,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else load_chunks()
        self.embedder = embedder or get_embedder()
        store = vector_store or get_vector_store()
        self._sparse = BM25Index(self.chunks)
        self._dense = DenseIndex(self.chunks, self.embedder, store=store)
        self._reranker = reranker or get_reranker()
        self._resolver = record_resolver
        self._vector_backend = self._dense.backend_name

    async def search(
        self,
        query: str,
        *,
        k: int = 5,
        alpha: float = 0.5,
        method: FusionMethod = "rrf",
        retrieve_k: int | None = None,
    ) -> SearchResult:
        settings = get_settings()
        raw_query = query
        if settings.enable_rag_safety:
            if detect_injection(query):
                return SearchResult(query=raw_query, chunks=[])
            query = sanitize_query(query)
        if settings.enable_query_rewrite:
            query = rewrite_query(query)

        deterministic = await self._resolve_deterministic(query)
        pool_k = retrieve_k or max(k * 2, k)
        sub_queries = decompose_query(query)
        merged: list[RetrievedChunk] = []
        seen: set[str] = set()
        for sq in sub_queries:
            for rc in self._retrieve_text(sq, k=pool_k, alpha=alpha, method=method):
                if rc.provenance.chunk_id and rc.provenance.chunk_id not in seen:
                    seen.add(rc.provenance.chunk_id)
                    merged.append(rc)
        merged = await self._reranker.rerank(query, merged, pool_k)
        chunks = merged[:k]
        for c in chunks:
            if "rerank" not in c.provenance.signals:
                c.provenance.signals.append("rerank")
            if self._vector_backend not in c.provenance.signals:
                c.provenance.signals.append(f"vector:{self._vector_backend}")
        confidence = _confidence_from_chunks(chunks)
        return SearchResult(
            query=raw_query, chunks=chunks, deterministic=deterministic, confidence=confidence
        )

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
        signals = list(f.signals)
        signals.append(f"vector:{self._vector_backend}")
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
                signals=signals,
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
        except Exception:  # noqa: BLE001
            return None
