# System design drill 7 — Second specialist agent via A2A

**Time:** 20 min

## Prompt

Add a Creative Review specialist without coupling codebases. How do discovery, task lifecycle,
failure handling, and security work?

<details>
<summary>Model answer</summary>

**Discovery:** peer serves Agent Card at `/.well-known/agent-card.json`; hub A2A client reads skills.

**Delegation:** hub sends A2A Task (JSON-RPC `message/send`); streams status over SSE.

**Lifecycle:** submitted → working → input-required (HITL) → completed | failed.

**Opaque boundary:** sanitize peer Artifacts; treat text as data; reject instruction injection.

**Failure:** review rejected → hub fails task before HITL; no connector side effects.

**No shared repo:** only protocol contract + card URL — not shared Python imports.
</details>
