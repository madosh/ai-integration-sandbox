# System design drill 3 — RAG over partner docs that change daily

**Time:** 25 min

## Prompt

Partner integration docs update daily. Design RAG that stays fresh and trustworthy.

<details>
<summary>Model answer</summary>

**Ingestion pipeline:** scheduled pull from doc source → chunk with metadata (partner, version, date) →
index sparse (BM25) + dense embeddings.

**Hybrid retrieval:** BM25 for rare terms/IDs; dense for semantic; RRF or alpha fusion.

**Deterministic path:** campaign id in query → authoritative connector record overrides/supplements text.

**Freshness:** version metadata in chunks; re-index on change; stale chunks flagged in provenance.

**Evals:** golden Q→doc labels; recall@k regression in CI; HITL queue for new doc changes.

</details>
