# Spec: connectors — reusable REST integration layer

## Goal

Provide a reusable layer that connects an internal system to MULTIPLE external partner APIs
("ad networks") that have deliberately different auth and pagination conventions. This is the
Oxigent core (REST GET/PUSH across networks) and the substrate for Factorial's integrations
framework. Adding a new partner must be cheap: one module + one registry entry.

## Inputs / Outputs

- **Inputs:** a `ConnectorConfig` (base URL, auth strategy + credentials, timeouts, retry policy) and
  per-call params (resource name, filters, pagination).
- **Outputs:**
  - `get_records()` -> async iterator of normalized Pydantic domain models (`Campaign`).
  - `push_record()` / `push_creative(file)` -> `PushResult` (with idempotency).
  - All raw partner payloads are mapped to normalized domain models.

## Behaviour

1. Each partner is implemented as a `Connector` subclass that owns a `ConnectorConfig` and uses a
   shared async `Transport` (no raw `httpx` in connector modules).
2. `Transport` wraps `httpx.AsyncClient` with: exponential backoff + jitter retries, `Retry-After`
   handling on HTTP 429, request timeouts, a circuit breaker, and structured request/response logging.
3. `paginate.py` exposes `cursor_paginate(...)` and `offset_paginate(...)` async generators so each
   connector iterates pages behind one `iterate(resource)` method regardless of style.
4. `AuthStrategy` is pluggable: `BearerAuth`, `ApiKeyAuth`, `BasicAuth` inject credentials per request.
5. `registry.py` makes connectors discoverable by name (the "integrations framework"): `get(name)`,
   `names()`, `register(name, factory)`.
6. Mock partners (in `mock_apis/`):
   - **PulseAds** — Bearer token, cursor pagination, JSON, rate-limited (429 + `Retry-After`).
   - **NovaReach** — API-key header, offset/limit pagination.
   - **CreativeBox** — basic auth, multipart creative upload (PUSH) + download (GET).

## Constraints

- Async-first; type hints + Pydantic v2 everywhere; offline (tests mount the mock app via
  `httpx.ASGITransport`, zero sockets).
- No raw `httpx` calls inside connector modules — everything goes through `Transport`.
- Retries are bounded; only 429 / 5xx / network errors are retried (never 4xx like 401).
- Pushes are idempotent: an `Idempotency-Key` derived from payload content dedupes server-side.
- Backoff/sleep is injectable so tests stay fast and deterministic.

## Failure modes

- **401/403** -> `AuthError` (typed, no retry).
- **404** -> `NotFoundError`.
- **429** -> honor `Retry-After`, retry up to the configured budget; exhausting it -> `RateLimitedError`.
- **5xx / network** -> backoff+jitter retry; exhausting it -> `UpstreamError`.
- **Repeated failures** -> circuit breaker opens and fails fast with `CircuitOpenError` until cooldown.

## Success criteria (measurable)

- `pytest tests/connectors` passes:
  - cursor pagination iterates across >1 page (PulseAds) and offset pagination too (NovaReach).
  - a forced 429 with `Retry-After` retries and then succeeds; the sleep honors `Retry-After`.
  - a multipart creative upload + download round-trip (CreativeBox), with idempotent re-upload.
  - auth failure surfaces `AuthError` (not a stack trace) and is not retried.
  - circuit breaker opens after N consecutive failures.
- Adding a 4th partner = a new module + one `registry.register(...)` line (proven by a tiny in-test
  example connector).

## Out of scope

- Real partner credentials / live networks (mock-only here).
- OAuth refresh flows, webhook ingestion, streaming uploads beyond multipart.
