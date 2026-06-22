# Communication protocols — MCP, A2A, AG-UI / A2UI

## Three-legged stool

```mermaid
flowchart TB
  subgraph clients ["Clients"]
    IDE["IDE / MCP client"]
    Peer["Peer A2A agent"]
    UI["React dashboard"]
  end

  subgraph hub ["AI Integration Hub"]
    MCP["MCP server — tools"]
    A2A["A2A server — tasks"]
    AGUI["AG-UI event stream"]
    A2UI["A2UI component specs"]
    Agent["Agent + HITL gate"]
  end

  IDE --> MCP
  Peer --> A2A
  UI --> AGUI
  AGUI --> A2UI
  MCP --> Agent
  A2A --> Agent
  AGUI --> Agent
```

## A2A task lifecycle

```mermaid
stateDiagram-v2
  [*] --> submitted: JSON-RPC message/send
  submitted --> working: hub starts agent run
  working --> input_required: side-effect skill
  input_required --> working: approve resume
  input_required --> failed: deny
  working --> completed: success
  working --> failed: error
  completed --> [*]
  failed --> [*]
```

## A2A publish flow (with peer review)

```mermaid
sequenceDiagram
  participant Client as A2A client
  participant Hub as Integration hub
  participant Review as CreativeReviewAgent
  participant Human as Human approver

  Client->>Hub: Task publish creative
  Hub->>Review: delegate review (opaque peer)
  Review-->>Hub: Artifact approved/rejected
  Hub->>Human: input-required / AG-UI card
  Human-->>Hub: approve
  Hub-->>Client: Task completed + Artifact
```

## AG-UI event categories

```mermaid
flowchart LR
  subgraph lifecycle ["Lifecycle"]
    L1["RUN_STARTED"]
    L2["STEP_STARTED/FINISHED"]
    L3["RUN_FINISHED/ERROR"]
  end

  subgraph text ["Text message"]
    T1["TEXT_MESSAGE_*"]
  end

  subgraph tool ["Tool call"]
    TC1["TOOL_CALL_*"]
  end

  subgraph state ["State"]
    ST1["STATE_SNAPSHOT"]
    ST2["STATE_DELTA"]
  end

  subgraph special ["Special"]
    SP1["INPUT_REQUEST"]
    SP2["CUSTOM — A2UI payloads"]
  end

  lifecycle --> Stream["SSE /agui/runs/id/stream"]
  text --> Stream
  tool --> Stream
  state --> Stream
  special --> Stream
```

## When to use which

| Protocol | Exposes | Best for | This repo |
|---|---|---|---|
| **MCP** | Typed tools (connectors, RAG) | IDE agents, fully controlled capabilities | `mcp_server/` |
| **A2A** | Whole agent + task lifecycle | Opaque / third-party / autonomous peers | `a2a/` + Agent Card |
| **AG-UI** | Event stream + lifecycle | Standardized agent→UI transport | `agui/events.py` |
| **A2UI** | Declarative UI payloads | Generative UI without React edits | `agui/a2ui.py` |

## A2A vs MCP tool — when to reach for A2A?

```mermaid
flowchart TD
  Q{"Do you own the code and schema?"}
  Q -->|Yes| MCP["Use MCP tool"]
  Q -->|No — opaque autonomous peer| A2A["Use A2A task + sanitize artifacts"]
```

Use **MCP** when you own the code, schema, and execution environment (call a tool directly).

Use **A2A** when the counterparty is an **opaque, autonomous agent** (different codebase, vendor, policy engine) that negotiates a **task** and returns **artifacts** you must sanitize.

## Opaque-agent principle

Peer agents are **untrusted**. Treat returned text as **data**, not instructions. Sanitize artifacts; watch for cross-agent prompt injection.

## HITL unification

| Layer | Expression |
|---|---|
| Agent | `approval.py` gate |
| A2A | `input-required` task state |
| AG-UI | `INPUT_REQUEST` + A2UI `ApprovalCard` |

## Version honesty

- **A2A:** target v0.2.x (JSON-RPC + SSE + Agent Card at `/.well-known/agent-card.json`)
- **AG-UI:** ~16–17 event types — pin shapes in `specs/agui.md`; spec still moving
- **A2UI:** youngest / least settled — illustrative field names only

Verify canonical specs before interviews: [a2a-protocol.org](https://a2a-protocol.org), [docs.ag-ui.com](https://docs.ag-ui.com).
