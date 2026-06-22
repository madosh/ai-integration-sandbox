# Spec: evals — measuring AI output quality

## Goal

Measure the quality of the AI surfaces (RAG retrieval, grounded generation, agent tool-selection)
with automated scorers plus a human-in-the-loop review path, and guard against regressions. This is
the platform's evals surface.

## Inputs / Outputs

- **Inputs:** golden datasets (`evals/datasets/*.jsonl`) of `{id, input, reference/rubric}`; the
  offline stack (FakeLLM, HashEmbedder, mock APIs).
- **Outputs:** a `Scorecard` (per-suite + flattened metrics), a timestamped JSON report in
  `evals/reports/`, a human review-queue export (CSV + JSON), and a non-zero exit code if any metric
  falls below its committed threshold.

## Behaviour

1. Suites:
   - **retrieval** — recall@k, MRR, nDCG@k against labelled relevant doc ids.
   - **generation** — `answer_from_docs` answers scored by an LLM-as-judge (rubric keyword coverage
     via the `LLMClient`).
   - **tool_selection** — the agent planner selects a skill for a goal; scored by exact match against
     the expected skill (accuracy).
2. Scorers (`evals/scorers.py`): `exact_match`, `structured_match`, `recall_at_k`, `mrr`,
   `ndcg_at_k`, `tool_selection_accuracy`, `llm_judge`.
3. The runner (`python tasks.py eval` -> `python -m aih.evals.runner`) runs all suites, prints a
   scorecard, writes a timestamped report, and enforces thresholds (`evals/thresholds.json`).
4. HITL review queue: export results to CSV/JSON with a blank `human_score`; a reviewed file is
   re-ingestable to merge human judgements back.

## Constraints

- Offline + deterministic (FakeLLM, HashEmbedder, mock APIs) so scores are reproducible in CI.
- Thresholds are committed; the runner fails (exit 1) on any metric below threshold.

## Failure modes

- Missing dataset -> clear error.
- Metric below threshold -> runner exits non-zero, listing the failing metrics.

## Success criteria (measurable)

- `pytest tests/evals` passes: scorers are correct on known inputs; an end-to-end eval run produces a
  scorecard across retrieval/generation/tool_selection; thresholds are enforced; the review queue
  round-trips (export then re-ingest a human score).
- `python tasks.py eval` prints a scorecard and writes a report under `evals/reports/`.

## Out of scope

- Real LLM judges / external eval services, statistical significance testing, large datasets.
