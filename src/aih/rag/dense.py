"""Dense retrieval via vector store + embedder."""

from __future__ import annotations

from aih.llm.base import Embedder
from aih.rag.models import Chunk
from aih.rag.vector_store import VectorStore, get_vector_store


class DenseIndex:
    """Dense index backed by a :class:`VectorStore` (in-memory or fake Pinecone)."""

    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Embedder,
        store: VectorStore | None = None,
    ) -> None:
        self.chunks = chunks
        self._embedder = embedder
        self._store = store or get_vector_store()
        self._backend = getattr(self._store, "backend_name", "memory")
        if chunks:
            ids = [c.id for c in chunks]
            vectors = embedder.embed([c.text for c in chunks])
            meta = [{"doc_id": c.doc_id} for c in chunks]
            self._store.upsert(ids, vectors, meta)

    def scores(self, query: str) -> list[float]:
        if not self.chunks:
            return []
        q = self._embedder.embed([query])[0]
        hits = self._store.search(q, len(self.chunks))
        by_id = dict(hits)
        return [float(by_id.get(c.id, 0.0)) for c in self.chunks]

    @property
    def backend_name(self) -> str:
        return self._backend
