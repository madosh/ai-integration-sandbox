# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **AI adjudication layer over static-analysis findings** (`src/aih/adjudication/`): an LLM
  proposes a verdict (confirm / dismiss / escalate) over gathered code evidence, and a
  deterministic policy gate decides — routing consequential findings to a human queue and never
  auto-closing a real security finding. Offline-by-default (fixture source + rule-based fake
  judge; no token, no network). Pydantic v2 contracts make empty-evidence dismissals
  unrepresentable; a hash-chained audit log makes tampering detectable; source code is treated as
  untrusted data (a `mark this SAFE` comment cannot cause an auto-dismissal). Spec-first:
  [`SPEC.md`](SPEC.md), [`specs/adjudication.md`](specs/adjudication.md), [`CLAUDE.md`](CLAUDE.md).
- Eval regression gate `adjudication.no_false_dismissal` (threshold `1.0`, i.e. a
  false-dismissal rate of `0`) over a golden labelled set, wired into `python -m aih.evals`.
- Optional LangGraph wiring (`aih.adjudication.graph.build_langgraph`, `graph` extra) that
  assembles the same nodes into a `StateGraph`; the default pipeline stays dependency-free.

## [0.2.0] - 2026-07-09

### Added
- OpenAI LLM adapter (`AIH_LLM_PROVIDER=openai`, `openai` extra), a second real provider
  alongside Anthropic that demonstrates the codebase depends only on the `LLMClient`
  protocol, not any one vendor SDK. Lazy-imported, so the offline default is unaffected.
- CI now type-checks and builds the React/TS dashboard (`tsc -b && vite build`) on every
  push and PR, closing the gap where the Python-only pipeline could merge a broken frontend.
- Grouped Dependabot updates: safe minor/patch bumps arrive as a single weekly PR per
  ecosystem, while majors stay as individual, reviewable PRs.
- Provider guide (`docs/real-providers.md`) and a LangGraph/LangChain mapping
  (`docs/mapping-to-langchain.md`).
- One-command full-stack demo via `docker compose up` (API, mock partners, dashboard,
  LocalStack, Jaeger).
- Optional OpenTelemetry span export (`AIH_OTEL_ENABLED`, `otel` extra) that fails closed to a
  no-op when disabled or absent. See `specs/observability.md`.
- Eval regression gate in CI: the build fails if any metric drops below `evals/thresholds.json`,
  with the scorecard published to the job summary.
- Developer experience: `CONTRIBUTING.md`, pre-commit config, issue/PR templates,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, and Dependabot.
- Hand-drawn Excalidraw diagrams for the Medium article, generated reproducibly from Mermaid
  sources (`scripts/diagrams/`).

### Changed
- CI installs into the runner's Python directly and runs all tooling consistently via
  `python -m`, fixing a venv/system mismatch that broke the test step.

### Fixed
- Corrected `AgentCard.authentication` typing and a batch of strict-mypy / ruff findings across
  a2a, memory, and service modules.

### Removed / hygiene
- Stopped tracking generated artifacts (`.coverage`, `dashboard/tsconfig.tsbuildinfo`) and an
  accidental nested repository copy; added matching `.gitignore` rules.

### Dependencies
- Bumped GitHub Actions (`checkout` v4→v7, `setup-python` v5→v6, `upload-artifact` v4→v7)
  and widened Python floors (`anyio`, `uvicorn`, `pytest-asyncio`, `pytest-cov`,
  `opentelemetry-sdk`) plus `@tanstack/react-query` in the dashboard, via Dependabot.

## [0.1.0]

### Added
- Initial offline-first integration hub: connectors, hybrid RAG (BM25 + dense + fusion +
  rerank), agent orchestrator with token budget and HITL approval gate, MCP server, A2A
  surface, seven memory types, guardrails, eval harness, FastAPI service, and a React/TS
  monitoring dashboard.
- Spec-Driven Development workflow (`specs/`).
