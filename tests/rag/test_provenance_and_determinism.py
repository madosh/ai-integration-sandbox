"""Provenance, alpha-sweep extremes, and the deterministic record path."""

from __future__ import annotations

import pytest

from aih.llm import HashEmbedder
from aih.rag.dense import DenseIndex
from aih.rag.models import AuthoritativeRecord, Provenance
from aih.rag.retriever import HybridRetriever
from aih.rag.sparse import BM25Index


@pytest.fixture
def retriever() -> HybridRetriever:
    # Default: load the real company-docs corpus, offline HashEmbedder.
    return HybridRetriever(embedder=HashEmbedder(dim=256))


async def test_results_carry_provenance(retriever: HybridRetriever) -> None:
    result = await retriever.search("how do I handle a 429 rate limit", k=3, method="rrf")
    assert result.chunks
    for rc in result.chunks:
        assert rc.provenance.source.startswith("doc:")
        assert rc.provenance.doc_id
        assert rc.provenance.chunk_id
        assert rc.provenance.method == "rrf"
        # at least one signal contributed
        assert rc.provenance.signals


async def test_alpha_sweep_extremes_reduce_to_pure_signals(retriever: HybridRetriever) -> None:
    query = "cursor pagination next cursor for campaigns"
    chunks = retriever.chunks
    sparse_scores = BM25Index(chunks).scores(query)
    dense_scores = DenseIndex(chunks, HashEmbedder(dim=256)).scores(query)
    sparse_top = chunks[max(range(len(sparse_scores)), key=lambda i: sparse_scores[i])].doc_id
    dense_top = chunks[max(range(len(dense_scores)), key=lambda i: dense_scores[i])].doc_id

    at_zero = await retriever.search(query, k=1, alpha=0.0, method="alpha")
    at_one = await retriever.search(query, k=1, alpha=1.0, method="alpha")

    assert at_zero.chunks[0].provenance.doc_id == sparse_top  # alpha=0 -> pure BM25
    assert at_one.chunks[0].provenance.doc_id == dense_top  # alpha=1 -> pure dense


async def test_deterministic_record_path() -> None:
    async def resolver(campaign_id: str) -> AuthoritativeRecord | None:
        if campaign_id == "nr-1":
            return AuthoritativeRecord(
                id="nr-1",
                partner="novareach",
                data={"title": "Brand Awareness", "status": "active"},
                provenance=Provenance(source="connector:novareach", method="deterministic"),
            )
        return None

    retriever = HybridRetriever(embedder=HashEmbedder(dim=256), record_resolver=resolver)
    result = await retriever.search("what is the status of campaign nr-1", k=3)

    assert result.deterministic is not None
    assert result.deterministic.id == "nr-1"
    assert result.deterministic.provenance.source == "connector:novareach"
    # Probabilistic retrieval still runs alongside the authoritative record.
    assert result.chunks


async def test_no_deterministic_match_without_id(retriever: HybridRetriever) -> None:
    result = await retriever.search("general question about onboarding", k=2)
    assert result.deterministic is None
