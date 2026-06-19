"""Sparse retrieval: BM25 over chunk tokens (probabilistic lexical match)."""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from aih.rag.chunking import tokenize
from aih.rag.models import Chunk


def _normalize(token: str) -> str:
    return token.lower()


class BM25Index:
    """A BM25 index over a fixed list of chunks."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self._corpus_tokens = [[_normalize(t) for t in tokenize(c.text)] for c in chunks]
        # rank_bm25 requires a non-empty corpus.
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def scores(self, query: str) -> list[float]:
        """Return a BM25 score per chunk (same order as ``self.chunks``)."""
        if self._bm25 is None:
            return []
        query_tokens = [_normalize(t) for t in tokenize(query)]
        return [float(s) for s in self._bm25.get_scores(query_tokens)]
