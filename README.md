# AI Integration Sandbox (`aih`)

An **offline-first, AI-native integration hub** covering two engineering profiles:

- **Product AI Engineering** (API & Integrations): Spec-Driven Development, AI Skills,
  Evals, RAG, human-in-the-loop + agentic workflows, MCP, end-to-end ownership.
- **Integration Engineering** (ad-tech): Python automations, REST GET/PUSH across
  ad networks, LLM + MCP inside the flow, a React/TS monitoring UI, AWS deploy, architecture +
  challenge-back.

It runs with **no external accounts or API keys by default**: the LLM is a deterministic `FakeLLM`,
embeddings use a deterministic `HashEmbedder`, and every external REST API is a local FastAPI fake in
`mock_apis/`. So `python tasks.py test` is fully offline and deterministic.

**Interview practice guide (HTML):** open [`docs/interview-practice.html`](docs/interview-practice.html) — **final study edition** (diagrams + modern AI map).

## Requirement -> module map

| Interview requirement | Source | Module |
|---|---|---|
| Advanced Python automations / services | both | `connectors/`, `service/` |
| REST consumption (GET) + publishing (PUSH) of data/files/creatives | Integration track | `connectors/` |
| Integrations framework / reusable capabilities | AI track | `connectors/base.py`, `skills/` |
| MCP server / tools | both | `mcp_server/` |
| LLM + agentic workflow orchestration | both | `agent/` |
| Human-in-the-loop on critical actions | AI track | `agent/approval.py` |
| RAG grounded in trusted data (probabilistic vs deterministic) | AI track | `rag/` (BM25 + dense + fusion) |
| Evals (automated + human-in-the-loop) | AI track | `evals/` |
| Spec-Driven Development | AI track | `specs/` (every feature has a spec first) |
| React / TypeScript monitoring UI | Integration track | `dashboard/` |
| AWS deploy / infra | both | `deploy/` (LocalStack-first) |
| Architecture + challenge-back | both | `docs/adr/`, `drills/` |

## Architecture at a glance

```mermaid
graph TB
  subgraph "Clients"
    Browser["Browser / API Client"]
    Dash["React Dashboard :5173"]
  end

  subgraph "FastAPI Service :8000"
    SVC["Routes\n/runs · /search · /chat\n/connectors · /skills · /a2a"]
    MW["Middleware\nrequest-id · api-key auth"]
  end

  subgraph "Agent"
    ORCH["Orchestrator\nplanning loop"]
    HITL["HITL Approval Gate\nside_effect=True skills"]
    LED["Run Ledger\nSQLite / in-memory"]
  end

  subgraph "Skills"
    S1["sync_campaign_data"]
    S2["publish_creative"]
    S3["answer_from_docs"]
  end

  subgraph "RAG"
    R1["BM25 sparse"]
    R2["Dense embed"]
    R3["Fusion RRF/alpha"]
    R4["Reranker + Safety"]
  end

  subgraph "Connectors"
    C1["PulseAds\nBearer token"]
    C2["NovaReach\nAPI key"]
    C3["CreativeBox\nOAuth2"]
  end

  LLM["LLM Client\nFakeLLM (offline) / Anthropic"]
  MOCK["Mock Partner APIs :9000"]
  EVALS["Eval Harness\nretrieval · generation · tool_selection"]

  Browser --> SVC
  Dash --> SVC
  MW --> SVC
  SVC --> ORCH
  SVC --> R1 & R2
  ORCH --> HITL
  ORCH --> S1 & S2 & S3
  ORCH --> LED
  S1 & S2 --> C1 & C2 & C3
  S3 --> R1 & R2
  R1 & R2 --> R3 --> R4
  S1 & S2 & S3 --> LLM
  C1 & C2 & C3 --> MOCK
  SVC --> EVALS
```

## Quick start

```bash
# 1. Create venv + install (uses .venv; no uv/make required)
python tasks.py setup

# 2. Run the test suite (offline, deterministic)
python tasks.py test

# 3. Boot the mock partner APIs (terminal A)
python tasks.py mock-apis

# 4. Boot the service (terminal B)
python tasks.py run

# 5. Run the dashboard (terminal C)
python tasks.py ui
```

> **Tooling note:** this repo ships both a `Makefile` and a stdlib-only `tasks.py`. On machines with
> GNU `make` you can use `make test` etc.; everywhere else use `python tasks.py test`. They are
> equivalent. If `uv` is installed it is preferred for installs, otherwise a `.venv` is used.

## Layout

```
ai-integration-sandbox/
  src/aih/
    config.py          # pydantic-settings Settings
    llm/               # LLMClient protocol + FakeLLM (default) + real adapter (env flag)
    connectors/        # REST integration layer (GET/PUSH across partner APIs)
    mcp_server/        # MCP tools exposing connector + RAG capabilities
    rag/               # hybrid retrieval: BM25 + dense + fusion (alpha & RRF)
    skills/            # reusable AI Skills the agent can invoke
    agent/             # orchestration loop + human-in-the-loop approval gate
    evals/             # eval harness (automated + HITL)
    service/           # FastAPI app wiring it all together
    observability/     # structured logging, request ids, SQLite run ledger
  mock_apis/           # local fake partner APIs (ad networks, docs store)
  dashboard/           # React + TS + Vite monitoring UI
  deploy/              # LocalStack + IaC
  drills/              # interview drill packs (katas, system-design, challenge-back)
  specs/               # Spec-Driven Development: one spec per feature
  tests/
```

## Key subsystems

### Hybrid RAG pipeline

```mermaid
flowchart LR
  Q["User query"] --> SF["Safety filter\ndetect_injection()\nsanitize_query()"]
  SF --> RW["Query rewrite\n(optional, LLM)"]
  RW --> SP["BM25 sparse\nrank_bm25\nexact keyword match"]
  RW --> DN["Dense embed\nHashEmbedder → cosine\nsemantic similarity"]
  SP --> FU["Fusion\nRRF — scale-free rank blend\nAlpha — weighted score mix"]
  DN --> FU
  FU --> RR["Reranker\ncross-encoder re-score"]
  RR --> OUT["SearchResult\nchunks + provenance\ndoc_id · chunk_id · signals"]
  Q --> DET["Deterministic path\ncampaign id? → connector lookup"]
  DET --> OUT

  style Q fill:#1e3a5f,color:#e0f2fe
  style OUT fill:#14532d,color:#dcfce7
  style DET fill:#3b1f5e,color:#f3e8ff
```

### Agent orchestration loop

```mermaid
sequenceDiagram
  participant C as Client
  participant S as FastAPI :8000
  participant A as Orchestrator
  participant L as LLM Planner
  participant SK as Skill
  participant G as Approval Gate

  C->>S: POST /runs {goal}
  S-->>C: {run_id, status:"running"}
  S->>A: run(goal, run_id) [background task]

  loop Planning loop (≤ agent_max_steps)
    A->>L: plan_next_step(goal, history, token_budget)
    L-->>A: {skill_name, args} or DONE

    alt skill has side_effect = True
      A->>G: request_approval(step)
      G-->>C: SSE: needs_approval
      C->>S: POST /runs/{id}/approve
      G-->>A: approved / denied
    end

    A->>SK: skill.run(args, ctx)
    SK-->>A: result (typed Pydantic output)
    A->>S: ledger.save(trace)
    S-->>C: SSE /runs/{id}/stream: update
  end

  A-->>S: trace.status = "completed"
  S-->>C: SSE: RUN_FINISHED
```

### Connector & transport stack

```mermaid
graph LR
  subgraph "Skills (callers)"
    SYN["sync_campaign_data"]
    PUB["publish_creative"]
  end

  subgraph "Connector layer"
    REG["ConnectorRegistry\n.get(name)"]
    PA["PulseAdsConnector\nBearer token header"]
    NR["NovaReachConnector\nX-Api-Key header"]
    CB["CreativeBoxConnector\nBasic auth → OAuth2 refresh"]
  end

  subgraph "Transport"
    TR["Transport\nhttpx.AsyncClient\nretry + exponential backoff\ncircuit breaker"]
    PAG["Pagination\ncursor / offset iterator"]
    HLT["Health check\nGET /health per connector"]
  end

  SYN & PUB --> REG
  REG --> PA & NR & CB
  PA & NR & CB --> TR
  TR --> PAG
  TR --> HLT
  PAG --> APIS["Partner APIs\n:9000 local mock\nor live REST endpoints"]
```

### Eval harness

```mermaid
graph LR
  DS["Golden datasets\nevals/datasets/*.jsonl\n{id, input, reference}"]

  DS --> RS["Retrieval suite\nrecall@k · MRR · nDCG@k"]
  DS --> GS["Generation suite\nLLM-as-judge\nrubric keyword coverage"]
  DS --> TS["Tool-selection suite\nexact match accuracy"]
  DS --> RD["Red-team suite\nrefusal / injection probes"]

  RS & GS & TS & RD --> SC["Scorecard\nper-suite metrics"]
  SC --> TH["Threshold check\nevals/thresholds.json\nexit 1 if below"]
  SC --> RPT["Timestamped report\nevals/reports/*.json"]
  SC --> HQ["HITL review queue\nexport CSV/JSON\n→ re-ingest human scores"]
```

## Spec-Driven Development

No feature is written before its spec exists in `specs/<feature>.md`, using
[`specs/_TEMPLATE.md`](specs/_TEMPLATE.md): Goal, Inputs/Outputs, Behaviour, Constraints, Failure
modes, Success criteria (measurable), Out of scope. Commits reference the spec id.

## Build phases

This repo was built phase-by-phase (each phase spec-first, tested, committed):

0. Skeleton 1. Connectors 3. Hybrid RAG 2. MCP server 4. Skills + agent + HITL
5. Evals 6. FastAPI service 7. Dashboard 8. Deploy/LocalStack 9. Drill packs
