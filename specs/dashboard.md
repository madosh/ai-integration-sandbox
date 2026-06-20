# Spec: dashboard — React monitoring UI

## Goal

A small monitoring UI showing automation status and pilot value: runs, approvals, metrics,
and registry introspection — wired to the FastAPI service.

## Inputs / Outputs

- **Inputs:** Service API at `http://127.0.0.1:8000` (proxied in dev).
- **Outputs:** Live runs table (SSE), run detail with Approve/Deny, metrics header, connectors/skills panel.

## Behaviour

1. Metrics header: total runs, success rate, records synced, creatives pushed, estimated value.
2. Runs table with status, goal, duration; live updates via SSE per run or polling list.
3. Run detail drawer: agent trace steps; PENDING APPROVAL with Approve/Deny → `POST /runs/{id}/approve`.
4. Connectors/skills panel from registry endpoints.
5. Typed API client (no `any`).

## Constraints

- Vite + React + TypeScript + TanStack Query.
- Dependency-light; monitoring layer, not a design exercise.

## Failure modes

- Service down → error state in UI.
- SSE disconnect → fall back to polling.

## Success criteria (measurable)

- `python tasks.py ui` runs dev server; approving in UI advances a real agent run.

## Out of scope

- Auth, multi-user, mobile layout polish.
