# Protocols & memory — drill model answers

Click to expand each answer during rehearsal.

<details>
<summary>1. The 7 memory types — which do you BUILD vs which is a BOUNDARY?</summary>

**Build:** working, semantic, episodic, procedural, external, prospective — unified in `MemoryManager`.

**Boundary:** parametric (= model weights). Don't fake it; explain externalize-vs-parametric trade-off.

Maps to existing infra: episodic ≈ run ledger, external ≈ RAG, procedural ≈ skills registry.
</details>

<details>
<summary>2. Externalize vs keep parametric?</summary>

Externalize volatile, per-tenant, auditable, deletable facts (GDPR). Keep parametric for general reasoning
patterns that are expensive to retrieve every turn and unsafe to store as rows (PII in weights is worse).

Cost/latency: retrieval adds ms; weights are amortized. Staleness: facts update without retraining.
</details>

<details>
<summary>3. Consolidation / reflection / forgetting</summary>

`reflect()` after each run → episodic index. `consolidate()` periodically distills successful episodes
into procedural heuristics via deterministic FakeLLM rules. TTL + salience eviction prevents unbounded growth.
</details>

<details>
<summary>4. MCP vs A2A vs AG-UI vs A2UI</summary>

MCP = tools you own. A2A = opaque peer agents + task lifecycle. AG-UI = event transport. A2UI = declarative
UI payloads on that stream. Three legs; HITL gate is the same pause in all three.
</details>

<details>
<summary>5. When A2A instead of an MCP tool?</summary>

When the counterparty is autonomous, separately deployed, or policy-bound (e.g. CreativeReviewAgent) —
you delegate a **task**, sanitize **artifacts**, and don't import their code as a typed tool.
</details>

<details>
<summary>6. Cross-agent prompt injection</summary>

Peer text is **data**. Sanitize artifacts; never `eval` or concatenate into system prompts blindly.
Log and flag instruction-like patterns. Same mindset as RAG injection guardrails.
</details>
