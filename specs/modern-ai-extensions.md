# Spec: modern AI extensions (Phases 10–14)

## Goal

Extend the sandbox with production-adjacent patterns: vector store protocol, reranking,
query rewrite, guardrails, tracing, MCP resources/prompts, streaming, online evals, and
connector reliability patterns — all offline-first by default.

## Success criteria

- `pytest` passes; `python tasks.py eval` includes rerank uplift metric.
- MCP exposes resources + prompts; `AGENTS.md` and agent card exist.
- Tracing spans appear on agent runs; budget can stop over-long loops.
- `docs/interview-practice.html` documents the full final study surface.
