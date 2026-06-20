# Challenge-back drill 3

**Stakeholder:** "Use only vector search — BM25 is legacy."

<details>
<summary>Counter-argument + alternative</summary>

Dense alone misses exact IDs, error codes, and rare partner tokens. **Alternative:** hybrid BM25 +
dense with RRF; deterministic connector lookup for structured ids like `pa-1`.

</details>
