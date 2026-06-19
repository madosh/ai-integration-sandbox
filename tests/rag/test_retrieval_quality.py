"""Hybrid retrieval quality on a tiny, controlled labeled set.

We use a synthetic corpus engineered around the one real difference between BM25
and the offline HashEmbedder: BM25 weights rare terms (IDF) while cosine over
hashed term counts does not. This produces queries where each pure signal ranks
the gold document differently, so fusion can be shown to help.
"""

from __future__ import annotations

import pytest

from aih.llm import HashEmbedder
from aih.rag.dense import DenseIndex
from aih.rag.models import Chunk
from aih.rag.retriever import HybridRetriever
from aih.rag.sparse import BM25Index

# Synthetic corpus: 'c' is a low-IDF common term; 'ra'/'r2' are rare (high IDF).
_DOCS = [
    ("DA", "ra c"),
    ("D2", "r2 c"),
    ("C1", "c c c c"),
    ("C2", "c c c"),
    ("F1", "foo bar"),
    ("F2", "baz qux"),
    ("F3", "lorem ipsum"),
]

# (query, gold doc id). Q1 favors the rare term (BM25-friendly); Q2 piles on the
# common term while a rare term distracts BM25 (dense-friendly).
_LABELED = [("ra c c c", "DA"), ("c c c c r2", "C1")]


def _chunks() -> list[Chunk]:
    return [Chunk(id=f"d{i}", doc_id=did, text=txt) for i, (did, txt) in enumerate(_DOCS)]


def _rank_of_gold(scores: list[float], chunks: list[Chunk], gold: str) -> int:
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    for rank, idx in enumerate(order, start=1):
        if chunks[idx].doc_id == gold:
            return rank
    return len(scores) + 1


def _mrr(ranks: list[int]) -> float:
    return sum(1.0 / r for r in ranks) / len(ranks)


@pytest.fixture
def retriever() -> HybridRetriever:
    return HybridRetriever(chunks=_chunks(), embedder=HashEmbedder(dim=256))


async def _hybrid_rank(retriever: HybridRetriever, query: str, gold: str, *, method, alpha=0.5):  # type: ignore[no-untyped-def]
    result = await retriever.search(query, k=len(_DOCS), alpha=alpha, method=method)
    for rank, chunk in enumerate(result.chunks, start=1):
        if chunk.provenance.doc_id == gold:
            return rank
    return len(_DOCS) + 1


async def test_hybrid_never_worse_and_beats_one(retriever: HybridRetriever) -> None:
    chunks = retriever.chunks
    sparse = BM25Index(chunks)
    dense = DenseIndex(chunks, HashEmbedder(dim=256))

    bm25_ranks, dense_ranks, rrf_ranks, alpha_ranks = [], [], [], []
    for query, gold in _LABELED:
        bm25_ranks.append(_rank_of_gold(sparse.scores(query), chunks, gold))
        dense_ranks.append(_rank_of_gold(dense.scores(query), chunks, gold))
        rrf_ranks.append(await _hybrid_rank(retriever, query, gold, method="rrf"))
        alpha_ranks.append(await _hybrid_rank(retriever, query, gold, method="alpha"))

    bm25_mrr = _mrr(bm25_ranks)
    dense_mrr = _mrr(dense_ranks)
    rrf_mrr = _mrr(rrf_ranks)
    alpha_mrr = _mrr(alpha_ranks)

    weakest = min(bm25_mrr, dense_mrr)
    eps = 1e-9
    # Hybrid is never worse than either pure method...
    for hybrid_mrr in (rrf_mrr, alpha_mrr):
        assert hybrid_mrr >= bm25_mrr - eps
        assert hybrid_mrr >= dense_mrr - eps
        # ...and strictly better than at least one of them.
        assert hybrid_mrr > weakest + eps


async def test_fusion_rescues_a_failing_signal(retriever: HybridRetriever) -> None:
    # On Q1 the pure-dense signal ranks the gold poorly (the common term pulls the
    # C-docs up), but alpha fusion recovers it to rank 1.
    query, gold = _LABELED[0]
    dense = DenseIndex(retriever.chunks, HashEmbedder(dim=256))
    dense_rank = _rank_of_gold(dense.scores(query), retriever.chunks, gold)
    alpha_rank = await _hybrid_rank(retriever, query, gold, method="alpha", alpha=0.5)

    assert dense_rank > 1  # pure dense fails to put the gold first
    assert alpha_rank == 1  # fusion rescues it
