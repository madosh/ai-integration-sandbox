"""External memory — thin wrapper over hybrid RAG."""

from __future__ import annotations

from aih.memory.models import RecallResult
from aih.rag.retriever import HybridRetriever


class ExternalMemory:
    def __init__(self, retriever: HybridRetriever) -> None:
        self._retriever = retriever

    async def recall(self, query: str, k: int = 3) -> list[RecallResult]:
        result = await self._retriever.search(query, k=k, method="rrf")
        out: list[RecallResult] = []
        for chunk in result.chunks:
            out.append(
                RecallResult(
                    type="external",
                    id=chunk.provenance.chunk_id or chunk.provenance.doc_id or "",
                    text=chunk.text[:400],
                    score=chunk.score,
                    source=f"rag:{chunk.provenance.doc_id}",
                    metadata={"signals": chunk.provenance.signals},
                )
            )
        return out
