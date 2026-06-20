# System design drill 1 — Integration framework for N ad networks

**Time:** 25 min

## Prompt

Design an integration framework that connects an internal campaign system to N ad network APIs
with different auth, pagination, and payload shapes. Teams will add new partners quarterly.

**Requirements sketch:**

- Pluggable connectors per partner
- Shared transport (retries, rate limits, circuit breaker)
- Normalized domain models
- Registry for discovery
- Offline testability

## Your sketch

(API boundaries, data model, connector interface, failure modes)

<details>
<summary>Model answer</summary>

**Core abstraction:** `Connector` ABC with `get_records()` / `push_*()`, `ConnectorConfig` (base URL,
auth strategy), shared `AsyncTransport` (httpx + backoff + 429 Retry-After + circuit breaker).

**Pagination:** `iterate(resource)` hiding cursor vs offset behind one async iterator.

**Registry:** name → factory; adding partner = new module + `register("partner", build_fn)`.

**Normalization:** raw JSON → Pydantic models per partner + canonical `Campaign` / `Creative`.

**Testing:** mock_apis FastAPI fakes + ASGI transport; no raw httpx in partner modules.

**Failure modes:** auth errors (fail fast), rate limits (backoff), circuit open (fail fast with metric),
partial page failure (retry page, idempotent writes).

**Trade-offs:** thin adapters vs heavy ETL in connector; prefer thin adapters + shared pipeline stages.

</details>
