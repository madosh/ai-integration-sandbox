# FastAPI in the AI Integration Hub

## Why FastAPI here?

FastAPI is the **composition root** of the runnable sandbox: it wires the agent, RAG, connectors,
memory, protocol adapters (A2A, AG-UI), and observability into one async HTTP surface suitable for
the React dashboard, tests, and interview demos.

## Architecture role

```mermaid
flowchart LR
  subgraph fastapi ["FastAPI service :8000"]
    Routes["HTTP routes"]
    SSE["SSE streams"]
    Lifespan["lifespan + AppState"]
    Middleware["CORS + request-id"]
  end

  subgraph wired ["Wired subsystems"]
    Agent["Agent orchestrator"]
    RAG["HybridRetriever"]
    Ledger["SQLiteLedger"]
    Memory["MemoryManager"]
    A2A["A2AServer"]
    AGUI["AguiBridge"]
    Approver["APIApprover"]
  end

  Dashboard["React :5173"] --> Routes
  Routes --> Agent
  Routes --> RAG
  Routes --> A2A
  SSE --> AGUI
  Agent --> Ledger
  Agent --> Memory
  Agent --> Approver
```

## AppState dependency graph

```mermaid
flowchart TB
  BS["build_state()"] --> AS["AppState"]
  AS --> L["ledger: RunLedger"]
  AS --> AP["approver: APIApprover"]
  AS --> MEM["memory: MemoryManager"]
  AS --> A2A["a2a_server"]
  AS --> BR["agui_bridge"]
  AS --> SUB["_subscribers / _agui_subscribers"]

  BA["build_agent()"] --> AG["Agent"]
  L --> AG
  AP --> AG
  MEM --> AG

  Routes["app.py routes"] --> AS
  Routes --> BA
```

## HTTP surface map

```mermaid
flowchart TB
  subgraph sync ["REST / JSON-RPC"]
    POST_RUNS["POST /runs"]
    POST_APPROVE["POST /runs/id/approve"]
    POST_SEARCH["POST /search"]
    POST_CHAT["POST /chat"]
    POST_A2A["POST /a2a"]
    POST_AGUI_IN["POST /agui/runs/id/input"]
  end

  subgraph streams ["SSE EventSource"]
    SSE_RUN["GET /runs/id/stream"]
    SSE_AGUI["GET /agui/runs/id/stream"]
    SSE_A2A["GET /a2a/tasks/id/events"]
    SSE_SEARCH["POST /search/stream"]
  end

  subgraph discovery ["Discovery / ops"]
    CARD["GET /.well-known/agent-card.json"]
    SKILLS["GET /skills"]
    METRICS["GET /metrics"]
    HEALTH["GET /healthz"]
  end
```

## Key modules

| Module | Role |
|---|---|
| `service/app.py` | Route definitions, SSE generators, JSON models |
| `service/deps.py` | `AppState` — shared ledger, approver, memory, subscribers |
| `service/chat.py` | Multi-turn RAG chat (separate from agent loop) |
| `service/webhooks.py` | Partner callback intake |

## Publish creative — sequence

```mermaid
sequenceDiagram
  autonumber
  participant UI as Dashboard
  participant API as FastAPI
  participant St as AppState
  participant Ag as Agent
  participant G as APIApprover
  participant C as Connector

  UI->>API: POST /runs
  API->>St: create_task(_run_agent)
  API-->>UI: run_id
  St->>Ag: run(goal)
  Ag->>G: publish_creative gate
  G-->>St: pending (blocks coroutine)
  St-->>UI: AG-UI INPUT_REQUEST via SSE
  UI->>API: POST /agui/runs/id/input approve
  API->>G: resolve()
  Ag->>C: push creative
  C-->>Ag: success
  Ag-->>St: trace completed
  St-->>UI: RUN_FINISHED SSE
```

## How we use it in the AI application

### 1. Dependency injection via `AppState`

`build_state()` constructs a single `AppState` attached to `app.state.aih` at startup. Routes never
instantiate agents directly — they call `app_state.build_agent()`, `build_retriever()`, etc.
This keeps tests able to inject `InMemoryLedger`, `APIApprover`, and mock HTTP transports.

### 2. Background agent runs

`POST /runs` spawns `asyncio.create_task(_run_agent(...))` so the HTTP request returns immediately
with a `run_id`. The ledger's `save()` is monkey-patched to `notify()` subscribers — powering both
legacy `/runs/{id}/stream` and AG-UI `/agui/runs/{id}/stream`.

### 3. Human-in-the-loop over HTTP

`APIApprover` blocks the agent coroutine on side-effecting skills. `POST /runs/{id}/approve` (or
`POST /agui/runs/{id}/input`) calls `resolve()`, unblocking the agent. Same gate drives A2A
`input-required`.

### 4. SSE for live UX

- `/runs/{id}/stream` — trace JSON updates (dashboard legacy path)
- `/agui/runs/{id}/stream` — typed AG-UI events + A2UI payloads
- `/search/stream` — RAG token streaming
- `/a2a/tasks/{id}/events` — A2A task lifecycle

`sse-starlette` `EventSourceResponse` keeps connections ordered and ping-alive.

### 5. Offline-first testing

```mermaid
flowchart LR
  Test["pytest + httpx"] --> ASGI["ASGITransport"]
  ASGI --> App["create_app(build_state(...))"]
  App --> Agent["Full agent loop — no TCP"]
```

Integration tests use `httpx.ASGITransport(app=create_app(build_state(...)))` — no TCP, no keys.
The same app factory powers local dev, CI, and interview-room demos.

## Interview talking points

- **Async all the way:** agent, connectors, RAG search are `async`; FastAPI matches without thread pools.
- **Thin routes, fat domain:** routes validate I/O; orchestration lives in `agent/`, `memory/`, `a2a/`.
- **One process, many protocols:** REST for CRUD, SSE for streams, JSON-RPC for A2A — same `AppState`.
- **12-factor config:** `AIH_*` env vars via `pydantic-settings`; no secrets in code.
