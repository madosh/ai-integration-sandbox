"""Dense retrieval: embedding cosine similarity (offline HashEmbedder by default)."""

from __future__ import annotations

import math

from aih.llm.base import Embedder
from aih.rag.models import Chunk


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class DenseIndex:
    """A dense index: precomputed chunk embeddings + cosine query scoring."""

    def __init__(self, chunks: list[Chunk], embedder: Embedder) -> None:
        self.chunks = chunks
        self._embedder = embedder
        self._vectors = embedder.embed([c.text for c in chunks]) if chunks else []

    def scores(self, query: str) -> list[float]:
        """Return a cosine similarity score per chunk."""
        if not self._vectors:
            return []
        q = self._embedder.embed([query])[0]
        return [cosine(q, v) for v in self._vectors]
