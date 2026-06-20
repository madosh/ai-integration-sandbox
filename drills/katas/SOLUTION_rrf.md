# Kata 4 — RRF

Score each doc: sum over rankings of `1 / (k + rank)`.

<details>
<summary>Model answer</summary>

```python
def reciprocal_rank_fusion(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda d: scores[d], reverse=True)
```

</details>
