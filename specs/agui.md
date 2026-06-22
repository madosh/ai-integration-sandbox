# Spec: agui — agent-to-UI protocol + A2UI generative components

## Goal

Replace ad-hoc run SSE with a standardized AG-UI event stream and declarative A2UI component specs
for the dashboard — same HITL gate as A2A `input-required`.

## Inputs / Outputs

- **Inputs:** run lifecycle; agent steps; user approve/deny/cancel via same channel.
- **Outputs:** typed AG-UI events (Lifecycle, Text, ToolCall, State, Custom); A2UI specs
  (ApprovalCard, MetricCard).

## Behaviour

1. `agui/events.py` — Pydantic models for ~16 event types in 5 categories.
2. `agui/bridge.py` — maps `RunTrace` + step changes → AG-UI events.
3. `agui/a2ui.py` — ApprovalCard + MetricCard declarative specs.
4. `GET /agui/runs/{id}/stream` — ordered SSE of AG-UI events.
5. `POST /agui/runs/{id}/input` — client decisions (approve, deny, cancel).
6. Dashboard AG-UI client + generic A2UI renderer (no hardcoded approval drawer).

## Constraints

- Pin target event shape in spec; AG-UI spec is young — names illustrative.
- Backward compatible: legacy `/runs/{id}/stream` may remain during migration.

## Failure modes

- Cancel → RUN_ERROR + run status cancelled.
- Malformed A2UI spec → CUSTOM event with parse error.

## Success criteria (measurable)

- Run drives dashboard via AG-UI events only for run detail panel.
- Approval card renders from A2UI spec; spec edit changes UI without React edits.
- STATE_DELTA keeps UI in sync; cancel stops run cleanly.

## Out of scope

- Full AG-UI reference SDK port.
- Mobile clients.
