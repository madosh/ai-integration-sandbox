# Running against real providers

The sandbox runs fully offline by default: a deterministic `FakeLLM`, a
deterministic `HashEmbedder`, and local mock partner APIs. Nothing below is
required to develop or to pass CI — it only matters when you want to exercise the
real path.

## Swap the LLM

Everything talks to the model through the `LLMClient` protocol
(`src/aih/llm/base.py`), so switching providers is configuration, not code.

```bash
# Anthropic
export AIH_LLM_PROVIDER=anthropic
export AIH_ANTHROPIC_API_KEY=sk-...
export AIH_ANTHROPIC_MODEL=claude-3-5-sonnet-latest
pip install -e ".[anthropic]"

# OpenAI
export AIH_LLM_PROVIDER=openai
export AIH_OPENAI_API_KEY=sk-...
export AIH_OPENAI_MODEL=gpt-4o-mini
pip install -e ".[openai]"
```

Both adapters import their vendor SDK lazily, so installing one extra never drags
the other in, and the default install stays dependency-light.

## Swap the partner APIs

The connectors default to the local mocks at `AIH_MOCK_API_BASE_URL`. Point them
at real endpoints and supply real credentials via the `AIH_PULSEADS_TOKEN`,
`AIH_NOVAREACH_API_KEY`, and `AIH_CREATIVEBOX_*` env vars (see `.env.example`).

## Embeddings

`HashEmbedder` stays the default even with a real LLM selected. There is no
first-party embeddings API for Anthropic; wire a provider (Voyage/OpenAI) into the
`Embedder` seam in `src/aih/llm/*` if you need real vectors. Keeping embeddings
deterministic is also what lets the retrieval evals assert on ranking rather than
fighting fluctuating scores.

## Keep real providers out of the deterministic gate

Real models are non-deterministic and metered — exactly what the unit-test and
eval gates are designed to avoid. Do not put them on the blocking CI path. The
recommended split:

- **Blocking, every push:** offline unit tests + the eval regression gate (fast,
  free, reproducible).
- **Non-blocking, scheduled:** an optional "live smoke" run against a real
  provider that confirms the adapter still round-trips a plan → tool-call.

An example workflow you can drop in as `.github/workflows/live-smoke.yml` (it is
gated on a repo secret, runs on a schedule or manually, and never blocks a PR):

```yaml
name: live-smoke
on:
  schedule:
    - cron: "0 6 * * 1"   # weekly, Monday 06:00 UTC
  workflow_dispatch:
jobs:
  smoke:
    runs-on: ubuntu-latest
    if: ${{ secrets.OPENAI_API_KEY != '' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev,openai]"
      - name: Plan a step against a real model
        env:
          AIH_LLM_PROVIDER: openai
          AIH_OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python - <<'PY'
          import anyio
          from aih.llm import get_llm
          from aih.llm.base import ChatMessage, ToolSpec

          tools = [ToolSpec(name="sync_campaign_data",
                            description="sync campaign records from a partner",
                            parameters={"type": "object",
                                        "properties": {"connector": {"type": "string"}}})]
          msgs = [ChatMessage(role="user", content="sync campaigns from novareach")]
          out = anyio.run(get_llm().tool_call, msgs, tools)
          assert out.tool_call is not None, out
          print("live smoke OK:", out.tool_call.name)
          PY
```

The point is not coverage — it is a canary that the real adapter still works, run
on your schedule and your dime, decoupled from the deterministic gate that guards
every merge.
