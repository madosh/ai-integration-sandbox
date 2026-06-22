# Spec: a2a — agent-to-agent protocol (v0.2.x target)

## Goal

Expose the integration hub as an A2A agent (JSON-RPC 2.0 + SSE) and delegate subtasks to opaque
peer agents. Complements MCP: MCP = tools, A2A = whole agents.

## Inputs / Outputs

- **Inputs:** JSON-RPC `message/send` with Task message; Agent Card discovery; client webhook URL.
- **Outputs:** Task lifecycle events (submitted → working → input-required → completed | failed);
  Artifacts as Parts; SSE `TaskStatusUpdateEvent` / `TaskArtifactUpdateEvent`.

## Behaviour

1. Serve Agent Card at `/.well-known/agent-card.json` (skills from registry).
2. `POST /a2a` JSON-RPC: `message/send` maps to internal agent run.
3. HITL bridge: internal `pending_approval` → A2A `input-required`; follow-up message resumes.
4. SSE at `/a2a/tasks/{id}/events` streams state transitions.
5. Push notifications: POST status to client-supplied webhook for long tasks.
6. Client discovers peer Agent Card and delegates (e.g. CreativeReviewAgent).
7. Sanitize peer Artifacts — treat text as data, not instructions.

## Constraints

- Offline-first: mock peer agent in `mock_agents/`; no external network in tests.
- Pin target: A2A v0.2.x shape in this spec; field names illustrative.

## Failure modes

- Unknown method → JSON-RPC error -32601.
- Denied HITL → terminal `failed` with zero side effects.
- Invalid peer artifact → rejected with reason.

## Success criteria (measurable)

- Agent Card served; skills discoverable.
- E2E: publish task → delegate review → input-required → approve → completed Artifact.
- Denial path → failed, no side effects.
- Webhook push tested for simulated long task.

## Out of scope

- Full Google A2A reference server compliance certification.
- Multi-agent mesh routing.
