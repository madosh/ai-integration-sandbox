# Spec: rag — hybrid retrieval (probabilistic + deterministic)

## Goal

Ground answers in trusted company data using hybrid retrieval that balances a probabilistic text
search (BM25 + dense) with a deterministic authoritative-record path. This is Factorial's RAG framing
and plays to a hybrid-search background. Results must be cited (provenance) so downstream answers are
auditable.

## Inputs / Outputs

- **Inputs:** a natural-language `query`, `k` (top results), `alpha` (fusion weight), and a fusion
  `method` ("alpha" or "rrf").
- **Outputs:** a `SearchResult` with:
  - ranked `RetrievedChunk`s, each carrying text, fused score, and `Provenance`
    (doc id + chunk id + per-signal scores + which signals contributed).
  - an optional `deterministic` `AuthoritativeRecord` when the query references a structured entity
    (e.g. a campaign id), labelled with connector provenance.

## Behaviour

1. `corpus/` holds small mock company docs (integration policies, partner specs, FAQ).
2. `chunking.py` splits docs into token-aware chunks with overlap, preserving metadata
   (doc id, title, source).
3. `sparse.py` builds a BM25 index over chunk tokens (`rank_bm25`).
4. `dense.py` embeds chunks with the `Embedder` interface (`HashEmbedder` by default, offline) and
   scores queries by cosine similarity.
5. `fusion.py` combines sparse + dense via (a) weighted **alpha** fusion over min-max-normalized
   scores and (b) **Reciprocal Rank Fusion** over rankings. `alpha` is a parameter.
6. `retriever.py`'s `HybridRetriever.search(query, k, alpha, method)` returns scored, cited chunks.
7. A deterministic path: if the query references a campaign id, an injected resolver fetches the
   authoritative connector record and it is returned alongside the retrieved text, labelled
   `connector:<partner>` rather than `doc:<id>`.

## Constraints

- Offline + deterministic (HashEmbedder; no network). Type hints + Pydantic v2 for results.
- Provenance is mandatory on every retrieved chunk.
- The deterministic resolver is injected (RAG stays decoupled from connectors/network).

## Failure modes

- Empty corpus / no matches -> empty `chunks` (no exception).
- Unknown/garbled query -> still returns best-effort ranking; deterministic path simply yields `None`.
- Resolver error -> deterministic path degrades to `None`; text retrieval still returns.

## Success criteria (measurable)

- `pytest tests/rag` shows hybrid retrieval is never worse than pure-BM25 or pure-dense on a tiny
  labeled query set (by MRR), and strictly better than at least one of them.
- Every returned chunk carries provenance (doc id + score + contributing signal).
- An alpha sweep (`alpha` in {0.0, 0.5, 1.0}) is testable and at the extremes reduces to the pure
  signals.
- The deterministic path returns the authoritative record (with `connector:` provenance) when a
  campaign id is present in the query.

## Out of scope

- Real embedding models / vector DBs, re-rankers, query rewriting, multi-hop retrieval.
