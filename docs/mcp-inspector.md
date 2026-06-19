# Testing the aih MCP server with the MCP Inspector

The MCP Inspector is a browser-based tool for exercising an MCP server by hand: list tools, inspect
their schemas, and call them with arbitrary arguments.

## Run the server

The server speaks the stdio transport:

```bash
python -m aih.mcp_server
```

By default its connector tools target the mock partner APIs at `AIH_MOCK_API_BASE_URL`
(`http://127.0.0.1:9000`), so start those first in another terminal:

```bash
python tasks.py mock-apis
```

## Launch the Inspector against it

The Inspector ships via `npx` (Node). Point it at the stdio command:

```bash
npx @modelcontextprotocol/inspector python -m aih.mcp_server
```

This spawns the server, connects, and opens the Inspector UI. From there you can:

- **List tools** — you should see `list_connectors`, `fetch_records`, `push_creative`,
  `get_run_status`, `search_docs`, each with a typed input schema.
- **Call `list_connectors`** — returns the three partners and their capabilities.
- **Call `fetch_records`** with `{"connector": "novareach"}` — returns normalized campaign records.
- **Call `push_creative`** with `{"connector": "creativebox", "file_ref": "s3://demo/banner.png"}` —
  returns a `requires_approval` envelope; note it does NOT upload anything (the agent layer resolves
  approvals).
- **Call `search_docs`** with `{"query": "rate limit 429"}` — returns cited hits from the company
  docs (hybrid RAG).

## Notes

- Every tool returns a structured envelope with `ok` plus data or a typed `error` — try an unknown
  connector (`{"connector": "nope"}`) and observe `error.type = "unknown_connector"` rather than a
  stack trace.
- For automated coverage, see `tests/mcp_server/test_tools.py`, which drives the same tools through
  the in-memory MCP client with the mock APIs mounted via an ASGI transport (fully offline).
