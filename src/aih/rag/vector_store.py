"""Vector store protocol — in-memory default + offline fake Pinecone adapter."""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from aih.config import get_settings


@runtime_checkable
class VectorStore(Protocol):
    """ANN-style vector index (offline implementations for the sandbox)."""

    def upsert(
        self, ids: list[str], vectors: list[list[float]], metadata: list[dict[str, str]]
    ) -> None: ...

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """Return (id, score) pairs sorted by similarity."""
        ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class InMemoryVectorStore:
    """Dict-backed vector index with cosine similarity."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._meta: dict[str, dict[str, str]] = {}

    def upsert(
        self, ids: list[str], vectors: list[list[float]], metadata: list[dict[str, str]]
    ) -> None:
        for id_, vec, meta in zip(ids, vectors, metadata, strict=True):
            self._vectors[id_] = vec
            self._meta[id_] = meta

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        scored = [(id_, _cosine(vector, v)) for id_, v in self._vectors.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    @property
    def backend_name(self) -> str:
        return "memory"


class FakePineconeVectorStore(InMemoryVectorStore):
    """Same as in-memory but labelled as a vector DB adapter for interview demos."""

    @property
    def backend_name(self) -> str:
        return "fake_pinecone"


def get_vector_store() -> VectorStore:
    backend = get_settings().vector_backend
    if backend == "fake_pinecone":
        return FakePineconeVectorStore()
    return InMemoryVectorStore()
