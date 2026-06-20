"""Reranker stage: second-pass scoring after hybrid retrieval."""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from aih.rag.models import RetrievedChunk

_WORD = re.compile(r"[a-z0-9]+")


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], k: int
    ) -> list[RetrievedChunk]: ...


class FakeReranker:
    """Offline reranker: keyword overlap boost (simulates cross-encoder lift)."""

    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], k: int
    ) -> list[RetrievedChunk]:
        q = set(_WORD.findall(query.lower()))

        def score(c: RetrievedChunk) -> float:
            tokens = set(_WORD.findall(c.text.lower()))
            overlap = len(q & tokens) / max(len(q), 1)
            return c.score + 0.5 * overlap

        ranked = sorted(chunks, key=score, reverse=True)
        return ranked[:k]


class NoReranker:
    async def rerank(
        self, query: str, chunks: list[RetrievedChunk], k: int
    ) -> list[RetrievedChunk]:
        return chunks[:k]


def get_reranker() -> Reranker:
    from aih.config import get_settings

    if get_settings().reranker == "fake":
        return FakeReranker()
    return NoReranker()
