# Architecture — AI Integration Hub

## Context

An offline-first integration hub connecting internal automation to multiple partner ad networks,
with RAG-grounded docs, MCP tools, agent orchestration, human-in-the-loop approvals, evals, and a
monitoring dashboard.

## C4 Container diagram

```mermaid
flowchart TB
  subgraph clients [Clients]
    Dashboard[React Dashboard]
    MCPClient[MCP Client / Inspector]
    CLI[CLI / Tests]
  end

  subgraph hub [AI Integration Hub]
    API[FastAPI Service]
    Agent[Agent Orchestrator]
    Skills[AI Skills]
    RAG[Hybrid RAG]
    MCP[MCP Server stdio]
    Connectors[Connector Framework]
    Evals[Eval Harness]
    Ledger[Run Ledger SQLite/DynamoDB]
  end

  subgraph partners [Partner Layer]
    MockAPIs[mock_apis FastAPI]
    PulseAds[PulseAds API]
    NovaReach[NovaReach API]
    CreativeBox[CreativeBox API]
  end

  subgraph aws [AWS / LocalStack]
    S3[S3 Creatives]
    SQS[SQS Approvals Queue]
    DDB[DynamoDB Run Ledger]
  end

  Dashboard --> API
  MCPClient --> MCP
  CLI --> API
  API --> Agent
  API --> RAG
  API --> Ledger
  Agent --> Skills
  Agent --> Ledger
  Skills --> Connectors
  Skills --> RAG
  MCP --> Connectors
  MCP --> RAG
  Connectors --> MockAPIs
  MockAPIs --> PulseAds
  MockAPIs --> NovaReach
  MockAPIs --> CreativeBox
  API --> S3
  API --> SQS
  Ledger --> DDB
```

## Key flows

1. **Read path:** Agent or dashboard triggers `sync_campaign_data` → connector GET with pagination →
   normalized records → optional LLM summary.
2. **Write path (HITL):** `publish_creative` → approval gate (API/CLI) → connector multipart PUSH →
   mock partner store / S3 archive.
3. **RAG path:** `POST /search` or `answer_from_docs` → hybrid BM25+dense fusion → cited chunks.
4. **Eval path:** `python tasks.py eval` → golden datasets → scorers → scorecard + regression thresholds.

## Publish flow (HITL write path)

```mermaid
sequenceDiagram
  participant UI as Dashboard
  participant API as FastAPI
  participant Agent as Orchestrator
  participant Gate as Approval gate
  participant Conn as Connector
  participant Partner as mock_apis

  UI->>API: POST /runs publish goal
  API->>Agent: plan + execute
  Agent->>Gate: publish_creative pending
  Gate-->>UI: approval required
  UI->>API: POST approve
  API->>Agent: resume
  Agent->>Conn: multipart push
  Conn->>Partner: POST creative
  Partner-->>Conn: 201 + id
  Conn-->>Agent: normalized result
  Agent-->>UI: trace complete
```

## Deployment topology (docker-compose)

| Service     | Port | Role                          |
|-------------|------|-------------------------------|
| service     | 8000 | FastAPI hub                   |
| mock-apis   | 9000 | Offline partner API fakes     |
| localstack  | 4566 | S3, SQS, DynamoDB emulation   |

IaC: `deploy/template.yaml` (SAM/CloudFormation) mirrors LocalStack resources provisioned by
`deploy/provision_localstack.py`.

## ADRs

- [001 — SQS for approvals](adr/001-sqs-approvals.md)
- [002 — S3 for creatives](adr/002-s3-creatives.md)
