// Mermaid sources for the three diagrams in docs/mediumarticle.html.
// Kept here so the SVGs can be regenerated: `npm run gen`.
// Line breaks in labels use \n (Excalidraw renders these natively).

export const diagrams = {
  architecture: `graph TB
  subgraph Clients
    Dash["React Dashboard"]
  end
  subgraph FastAPI_Service["FastAPI Service"]
    SVC["/runs · /search · /chat · /connectors"]
  end
  subgraph Agent
    ORCH["Orchestrator (planner loop)"]
    HITL["HITL Approval Gate"]
  end
  subgraph Deterministic_fakes["Deterministic fakes"]
    LLM["FakeLLM"]
    EMB["HashEmbedder"]
    MOCK["Mock partner APIs (local FastAPI)"]
  end
  RAG["Hybrid RAG\nBM25 + dense + fusion"]
  CONN["Connectors\nretry · backoff · circuit breaker"]
  Dash --> SVC --> ORCH
  ORCH --> HITL
  ORCH --> RAG
  ORCH --> CONN --> MOCK
  ORCH --> LLM
  RAG --> EMB`,

  "hitl-approval": `sequenceDiagram
  participant C as Dashboard
  participant S as FastAPI
  participant A as Agent
  participant G as Approval Gate
  C->>S: POST /runs {goal}
  S->>A: run(goal) [background task]
  A->>A: planner selects publish_creative
  A->>G: request approval — run PAUSES
  G-->>C: SSE: pending_approval
  C->>S: POST /runs/{id}/approve
  G-->>A: approved
  A->>A: skill executes → pushes creative
  A-->>C: SSE: RUN_FINISHED`,

  "rag-pipeline": `flowchart LR
  Q["Query"] --> SF["Safety filter\n(injection detection)"]
  SF --> SP["BM25 sparse"]
  SF --> DN["Dense embeddings"]
  SP --> FU["Fusion\nRRF / weighted alpha"]
  DN --> FU
  FU --> RR["Reranker"]
  RR --> OUT["Cited chunks\n+ provenance"]
  Q --> DET["Deterministic path:\ncampaign id → connector lookup"]
  DET --> OUT`,
};
