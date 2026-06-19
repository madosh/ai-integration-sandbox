# Spec: mcp — MCP server exposing integration + retrieval tools

## Goal

Expose the connector and RAG capabilities as Model Context Protocol (MCP) tools so an LLM/agent (or
the MCP Inspector) can drive integrations through a standard protocol. Both job descriptions name MCP
explicitly.

## Inputs / Outputs

- Tools (typed Pydantic args -> typed envelope results):
  - `list_connectors()` -> connectors + capabilities.
  - `fetch_records(connector, resource, filters, limit)` -> normalized records.
  - `push_creative(connector, file_ref, name)` -> `requires_approval` envelope (NOT executed).
  - `get_run_status(run_id)` -> run status (run ledger wired in Phase 6).
  - `search_docs(query, k)` -> cited hits + optional authoritative record (backed by Phase 3 RAG).
- Every tool returns a structured envelope with `ok` plus data or a typed `error`.

## Behaviour

1. Built on the official `mcp` SDK (`FastMCP`). `python -m aih.mcp_server` runs a stdio server.
2. A `ServerState` singleton holds an optional `httpx` transport (so tests mount the mock APIs
   in-process) and a `HybridRetriever`.
3. Side-effecting tools (`push_creative`) return a `requires_approval` envelope containing an
   `ApprovalRequest` (what / why / payload preview / reversibility). The MCP layer NEVER executes the
   side effect; the agent layer (Phase 4) resolves the approval.
4. `search_docs` delegates to `HybridRetriever`, returning hits with citations (provenance) and an
   optional deterministic record.

## Constraints

- Tools never raise raw exceptions across the protocol boundary; failures become typed error
  envelopes.
- Offline + deterministic in tests (mock APIs via ASGI transport, HashEmbedder).
- Typed args + results via Pydantic v2.

## Failure modes

- Unknown connector -> `ok=False`, `error.type="unknown_connector"` (not a stack trace).
- Unsupported operation -> `error.type="unsupported"`.
- Connector/transport error -> `error.type` is the exception class name.
- RAG failure -> `search_docs` returns `ok=False` with `error.type="search_error"`.

## Success criteria (measurable)

- `pytest tests/mcp_server` (via the in-memory MCP client):
  - `fetch_records` returns normalized records from the mock APIs.
  - `push_creative` returns a `requires_approval` envelope and does not upload.
  - unknown connector returns a typed error envelope, not an exception.
  - `search_docs` returns cited hits; `list_connectors` reports capabilities.
- `docs/mcp-inspector.md` documents testing with the MCP Inspector.

## Out of scope

- Auth/permissions on the MCP server, resources/prompts (tools only), remote transports.
