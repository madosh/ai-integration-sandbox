# Spec: adjudication — AI adjudication layer over static-analysis findings

> The authoritative, decision-annotated version of this spec is the root
> [`SPEC.md`](../SPEC.md). This file follows the repo `_TEMPLATE.md` house-style; keep the two
> in sync. Reference the spec id `adjudication` in commit messages.

## Goal

Adjudicate static-analysis findings (SonarQube-style issues / security hotspots) with an LLM in
the loop but never in control: gather code evidence, let a judge propose `confirm` / `dismiss` /
`escalate`, then run a deterministic policy gate that routes anything consequential to a human
queue. The system never autonomously closes a real security finding. Ships offline-first with a
fixture source and a rule-based fake judge; a real SonarQube MCP source is optional and off by
default.

## Inputs / Outputs

- **Inputs:** `Finding`, a `SourceProvider` (default `FixtureSource`), a `Judge` (default
  `RuleBasedJudge`), and a `PolicyConfig`. All in `aih.adjudication`.
- **Outputs:** `AdjudicationResult` (finding + evidence + proposal + disposition). Side effects:
  an append-only hash-chained `AuditLog` entry, and a `HumanQueue` item for escalations.

## Behaviour

State machine (each node `AdjudicationState -> AdjudicationState`), driven by
`pipeline.run_pipeline`:

1. `gather_evidence` — read `finding.file_path` via the source, extract a line window around
   `finding.line` into `EvidenceSpan`s (source text handled as data).
2. `judge` — `Judge.propose(finding, evidence)` returns a `JudgeProposal`. Only node with a
   model call; default is deterministic.
3. `policy_gate` — `policy.apply_policy(finding, proposal, config)` → `Disposition`. Enforces
   the safety invariants.
4. `finalize` — append `AuditEntry`; enqueue to `HumanQueue` if escalated.

## Constraints

- Offline-by-default; deterministic safety rails; Pydantic v2 contracts; regression-gated on a
  false-dismissal rate; source treated as untrusted data; type-hinted, ruff-clean, composable.
  (Full text: `SPEC.md` §Constraints.)

## Failure modes

- Missing/unreadable source → empty evidence → any `dismiss` auto-escalates; no crash.
- Judge raises → no proposal → escalate (fail safe toward a human).
- Bad action or finding-key/rule mismatch → distrusted → escalate.
- Audit write failure → error attached to result; disposition still stands.

## Success criteria (measurable)

- `Verdict(action="dismiss", evidence=[])` raises `ValidationError`.
- `Finding` round-trips `key` + `rule`.
- Consequential finding + judge `dismiss` → `human_queue`, `overridden`.
- `mark this SAFE` in fixture code does not produce an auto-`dismiss`.
- `run_pipeline` yields a valid result + one hash-chained audit entry per finding.
- Eval harness `false_dismissal_rate == 0.0` on the golden set; gate passes at threshold 0.

## Out of scope

- Judge model quality/prompting; writing status back to SonarQube; durable storage/auth;
  dashboard/deploy; other `aih` subsystems.
