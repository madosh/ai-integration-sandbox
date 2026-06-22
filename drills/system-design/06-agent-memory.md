# System design drill 6 — Memory for a long-horizon integration agent

**Time:** 20 min

## Prompt

Design memory for an integration agent that runs multi-day sync workflows across tenants.
Cover the seven memory types, consolidation, scoping, and decay.

<details>
<summary>Model answer</summary>

**Taxonomy:** working (token budget), semantic (facts), episodic (run ledger), procedural (skills +
learned playbooks), external (RAG), prospective (scheduled intentions), parametric = model boundary.

**Unifier:** one `MemoryManager` API — don't build seven silos.

**Consolidation:** episodic → procedural heuristics on success clusters; episodic → semantic facts
for stable preferences.

**Scoping:** `tenant_id` + `subject_id` on every row; `delete_subject()` for GDPR erasure.

**Decay:** TTL + salience eviction; summarize old episodes instead of deleting audit trail.

**Offline default:** SQLite + HashEmbedder; swap vector backend via protocol.
</details>
