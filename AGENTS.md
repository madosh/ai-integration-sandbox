# AI Integration Hub (`aih`) — agent instructions

This repo is an **offline-first AI integration sandbox** for building and testing API integrations
and GenAI workflows.

## Conventions

- Python 3.11+, Pydantic v2, async-first, type hints everywhere.
- Spec before code: read `specs/<feature>.md` before editing a module.
- Default stack is offline: `FakeLLM`, `HashEmbedder`, `mock_apis/` — no API keys in tests.
- Side-effecting skills require HITL approval (`agent/approval.py`).

## Key modules

| Area | Path |
|------|------|
| Connectors | `src/aih/connectors/` |
| Hybrid RAG + vector store | `src/aih/rag/` |
| Agent + budget + memory | `src/aih/agent/` |
| MCP tools/resources/prompts | `src/aih/mcp_server/` |
| Guardrails | `src/aih/guardrails/` |
| Evals | `src/aih/evals/` |
| Service API | `src/aih/service/` |
| Dashboard | `dashboard/` |

## Commands

```bash
python tasks.py setup
python tasks.py test
python tasks.py mock-apis   # :9000
python tasks.py run         # :8000
python tasks.py ui          # :5173
python tasks.py eval
```
