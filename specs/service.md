# Spec: service — FastAPI integration hub API

## Goal

Expose connectors, skills, RAG search, agent runs, HITL approval, metrics, and health checks
behind a typed FastAPI service the dashboard and integration tests can drive over HTTP.

## Inputs / Outputs

- **Inputs:** HTTP requests; env config (`AIH_*`); in-process agent, skills, RAG, ledger.
- **Outputs:** JSON responses; SSE run-progress streams; OpenAPI schema; SQLite-backed run ledger.

## Behaviour

1. `POST /runs` — start an agent run from a `goal` string; returns `run_id` immediately while the
   run executes in a background task.
2. `GET /runs/{id}` — status, full trace, value summary.
3. `POST /runs/{id}/approve` — resolve a pending HITL approval (`approved: bool`).
4. `GET /runs` — list runs (most recent first).
5. `GET /runs/{id}/stream` — SSE stream of trace updates until the run completes.
6. `GET /connectors`, `GET /skills` — registry introspection.
7. `POST /search` — RAG query with citations (`query`, optional `k`, `alpha`).
8. `GET /metrics` — automation counts, success rate, latency, estimated value (mock).
9. `GET /healthz` — liveness.

Observability: structured JSON logging, per-request id header, SQLite run ledger.

## Constraints

- Async-first; no blocking I/O on request paths.
- Offline-safe defaults (FakeLLM, mock API transport in tests).
- OpenAPI models are Pydantic v2.

## Failure modes

- Unknown run id → 404.
- Approve when no pending gate → 409.
- Invalid body → 422.

## Success criteria (measurable)

- `python tasks.py run` boots on :8000.
- Integration test drives full run + approval round-trip over HTTP.
- OpenAPI docs list all endpoints with typed schemas.

## Out of scope

- AuthN/AuthZ for external callers, multi-tenant isolation, horizontal scaling.
