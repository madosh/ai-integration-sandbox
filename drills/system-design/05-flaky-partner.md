# System design drill 5 — Flaky partner API resilience

**Time:** 20 min

## Prompt

One ad network API is flaky (429s, 5xx, slow). Prevent it from taking down the whole pipeline.

<details>
<summary>Model answer</summary>

**Per-partner isolation:** circuit breaker on transport; open circuit → fail fast for that partner only.

**Retries:** exponential backoff + jitter; honor Retry-After on 429; cap max attempts.

**Bulkhead:** separate connection pools / concurrency limits per connector.

**Queue-based workers:** SQS/Kafka per partner; one slow partner backs up its queue, not others.

**Degraded mode:** skip partner with alert; partial sync success reported in metrics.

**Observability:** structured logs with partner id, attempt count, breaker state.

</details>
