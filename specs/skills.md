# Spec: skills — reusable AI Skills

## Goal

Provide reusable, well-scoped capabilities the agent can invoke and that can be tested in isolation.
This is the "AI Skills" surface and mirrors the connector registry so capabilities are
discoverable.

## Inputs / Outputs

- Each Skill declares: `name`, `description`, `side_effect: bool`, a Pydantic `input_model`, and a
  Pydantic `output_model`. `run(payload, ctx)` executes it.
- A `SkillRegistry` exposes `names()`, `get(name)`, `describe()` and `tool_specs()` (for planners).

## Behaviour

Skills implemented:
- `sync_campaign_data` (read-only): pull records from one connector, normalize, compute totals, and
  summarize via the `LLMClient`.
- `publish_creative` (`side_effect=True`): push a creative to a connector. The agent MUST route this
  through the approval gate before `run()` is called.
- `answer_from_docs` (read-only): RAG-grounded Q&A returning an answer plus citations.

`SkillContext` carries the `LLMClient`, the connector registry (with an optional `httpx` transport so
skills run offline in tests), and a `HybridRetriever`.

## Constraints

- Type-safe I/O (Pydantic v2). Skills never perform a side effect unless explicitly invoked
  (the agent enforces approval for `side_effect=True`).
- Offline + deterministic under `FakeLLM` + mock APIs.

## Failure modes

- Invalid input -> `pydantic.ValidationError` surfaced to the agent as an error step.
- Connector/transport errors -> raised as `ConnectorError`; the agent records an error step.

## Success criteria (measurable)

- Each skill is unit-testable in isolation (mock APIs / FakeLLM): `sync_campaign_data` returns counts
  + a summary; `publish_creative` uploads and returns a `PushResult`; `answer_from_docs` returns an
  answer with non-empty citations.
- The registry lists all three skills with their `side_effect` flags and input schemas.

## Out of scope

- Long-running / streaming skills, skill versioning, dynamic skill loading from disk.
