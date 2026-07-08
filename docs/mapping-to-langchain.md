# Mapping the sandbox onto LangGraph / LangChain

This project is a self-contained reference, not a framework — it deliberately
implements its own small agent loop, retriever, and gate so every moving part is
visible and testable. If you already work in LangGraph/LangChain, this table
places each pattern so you can carry the ideas across (especially the
deterministic-testing ones) rather than adopting this stack wholesale.

| Sandbox piece | LangGraph / LangChain equivalent | Notes |
|---|---|---|
| `LLMClient` protocol (`llm/base.py`) | `BaseChatModel` / any `Runnable` | Same idea: depend on an interface, not a vendor SDK. |
| `FakeLLM` (deterministic) | `FakeListChatModel` / a custom `Runnable` stub | The sandbox's is rule-based (ranks tools, fabricates schema-valid args) rather than a fixed reply list, so it can drive a real loop. |
| `HashEmbedder` (deterministic) | `FakeEmbeddings` / `DeterministicFakeEmbedding` | Deterministic vectors are what make retrieval evals assertable. |
| Agent orchestrator loop (`agent/orchestrator.py`) | `StateGraph` / `create_react_agent` | Plan → select → gate → execute → observe, hand-rolled and traced. |
| HITL approval gate (`agent/approval.py`) | `interrupt()` / `interrupt_before` on a node | Both pause mid-run for a human decision; the sandbox parks on an `asyncio.Future` and enforces the gate in the orchestrator, not the tool. |
| Skills + registry (`skills/`) | `@tool` / `ToolNode` | Each skill declares `side_effect`, which the gate keys off. |
| `RunTrace` + SQLite ledger (`observability/`) | LangSmith tracing + a checkpointer | Step-level trace persisted for the dashboard and replay. |
| Hybrid RAG (`rag/`) | `EnsembleRetriever` (BM25 + vector) + a reranker | BM25 + dense + fusion (RRF/α) + cross-encoder rerank, plus a deterministic exact-lookup path for structured entities. |
| Evals as a CI gate (`evals/`) | LangSmith evaluators / custom pytest | The differentiator is *gating*: committed thresholds, exit non-zero on regression. |
| MCP server (`mcp_server/`) | `langchain-mcp-adapters` | Exposes the same skills to any MCP client. |
| A2A JSON-RPC surface (`a2a/`) | (no direct equivalent) | Agent-to-agent card + JSON-RPC endpoint. |

## The one idea worth stealing

Whatever framework you use, the reusable lesson is the **deterministic layer**:
put a reproducible fake behind every external boundary, assert on *structure and
ranking* rather than raw model output, and wire your evals as a blocking gate.
That is what lets `pytest` exercise an agent in CI without keys, cost, or flake —
and it is framework-agnostic.
