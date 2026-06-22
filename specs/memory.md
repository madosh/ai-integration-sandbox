# Spec: memory — unified agent memory (7 types)

## Goal

Provide one `MemoryManager` that unifies seven memory types for the integration agent,
reusing the run ledger, hybrid RAG embedder, and skills registry — no parallel stores.

## Inputs / Outputs

- **Inputs:** `MemoryItem` (type, tenant_id, subject_id, namespace, key, value, confidence,
  source); agent `RunTrace`; recall queries; token budget for working-memory assembly.
- **Outputs:** `RecallResult` list; `AssembledContext` (fragments + provenance + token estimate);
  consolidation report; episodic/procedural/semantic writes.

## Behaviour

1. **Working** (`working.py`): `ContextAssembler.build(goal, budget)` merges semantic facts,
   similar episodes, applicable procedures, due prospective intentions, and scratchpad notes.
   Evicts lowest-salience fragments when over budget. Ephemeral per run; returns provenance.
2. **Semantic** (`semantic.py`): `upsert(namespace, key, value, confidence, source)` with conflict
   resolution (newer + higher-confidence wins; contradictions flagged). `recall_by_key` and
   `recall_similar` via shared HashEmbedder.
3. **Episodic** (`episodic.py`): extends run ledger — indexes traces with outcome, lesson, goal
   embedding. `recall_similar(goal)` surfaces prior attempts.
4. **Procedural** (`procedural.py`): declared skills from registry + learned heuristics (versioned
   playbooks distilled from successful episodes).
5. **External** (`external.py`): thin wrapper over `HybridRetriever` — same embedder as semantic.
6. **Parametric:** boundary only — documented in `docs/memory-notes.md`, not implemented.
7. **Prospective** (`prospective.py`): intentions `{goal, trigger, status}`; `due()` surfaces
   items into working memory at agent tick.

**MemoryManager API:** `remember`, `recall`, `assemble_working_memory`, `consolidate`, `reflect`,
`delete_subject`.

**Agent wiring:** before plan → assemble + inject; after run → `reflect` + optional `consolidate`.

## Constraints

- Offline-first: SQLite + HashEmbedder; no network or API keys required for tests.
- Per-tenant namespaces (`tenant_id`); `delete_subject(subject_id)` for GDPR-style erasure.
- TTL + salience eviction on semantic facts and episode index.
- Deterministic consolidation via FakeLLM keyword rules.

## Failure modes

- DB missing → auto-create schema on first use.
- Over-budget assembly → evict scratchpad first, then oldest low-confidence semantic facts.
- Contradicting semantic facts → both kept with `contradiction=True` flag on newer entry.
- Episodic recall with no ledger → empty list (not an error).

## Success criteria (measurable)

- Fact written in run A recalled in run B (cross-run persistence).
- Failed approach flagged via episodic recall before repeat.
- Prospective intention due in run B surfaces in assembly from run A schedule.
- `assemble_working_memory` respects token budget and returns provenance per fragment.
- `consolidate()` turns N successful episodes into one procedural heuristic.
- Per-tenant scoping isolates memories; `delete_subject()` removes them.

## Out of scope

- Parametric memory (model weights).
- Real vector DB (adapter slot only; default in-memory/SQLite).
- OS-level reminders; cross-process distributed memory.
