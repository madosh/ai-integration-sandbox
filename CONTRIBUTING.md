# Contributing to AI Integration Sandbox

Thanks for your interest! This project is an **offline-first, AI-native integration hub**.
The guiding principle: everything runs deterministically with **no external accounts or API
keys** by default, so tests and evals are fast, free, and reproducible.

Please read this before opening a pull request.

## Ground rules

1. **Spec before code.** No feature lands without a spec in [`specs/<feature>.md`](specs/)
   (use [`specs/_TEMPLATE.md`](specs/_TEMPLATE.md)). Update the spec in the same PR as the code.
2. **Stay offline-first.** New code must work with `FakeLLM`, `HashEmbedder`, and the
   `mock_apis/` fakes. Real providers (Anthropic, OTel exporters, …) are always opt-in behind
   an extra + an env flag, and must degrade to a no-op when absent.
3. **Side effects require HITL.** Any skill that mutates partner state must set
   `side_effect=True` and pass through the approval gate (`agent/approval.py`).
4. **Types everywhere.** Python 3.11+, Pydantic v2, async-first, full type hints. `mypy` runs in
   `strict` mode.

## Local setup

```bash
python tasks.py setup     # create .venv and install -e ".[dev]"
python tasks.py test      # full suite, offline + deterministic
```

Everything is driven by the stdlib-only [`tasks.py`](tasks.py) (a `Makefile` mirrors it):

| Command | What it does |
|---|---|
| `python tasks.py test` | Run the pytest suite |
| `python tasks.py lint` | `ruff check` + `black --check` |
| `python tasks.py type` | `mypy` (strict) |
| `python tasks.py eval` | Run the eval harness + write a scorecard |
| `python tasks.py run` | Boot the FastAPI service on `:8000` |
| `python tasks.py mock-apis` | Boot the mock partner APIs on `:9000` |
| `python tasks.py ui` | Run the dashboard dev server on `:5173` |

## Quality gates (must pass before merge)

CI runs on Python 3.11 and 3.12 and blocks the merge unless **all** pass:

| Gate | Command | Bar |
|---|---|---|
| Lint + format | `python tasks.py lint` | clean |
| Static types | `python tasks.py type` | clean |
| Tests + coverage | `pytest --cov=aih --cov-fail-under=70` | ≥ 70% |
| Eval regression | `python tasks.py eval` | every metric ≥ `src/aih/evals/thresholds.json` |

Run all four locally before pushing. Optionally install the git hooks so lint/format run on
every commit:

```bash
pip install pre-commit
pre-commit install
```

## How to extend

### Add a partner connector

1. Spec it in `specs/connectors.md` (or a new spec) and read
   [`docs/runbooks/add-a-partner.md`](docs/runbooks/add-a-partner.md).
2. Subclass the base in `src/aih/connectors/base.py`; implement auth, pagination, and mapping.
3. Register it in `src/aih/connectors/registry.py`.
4. Add a matching fake to `mock_apis/` so it stays testable offline.
5. Add tests under `tests/connectors/`.

### Add an AI Skill

1. Add the skill in `src/aih/skills/`; declare `side_effect` correctly.
2. If it mutates partner state, ensure it routes through the approval gate.
3. Expose it via the MCP server (`src/aih/mcp_server/`) if it should be tool-callable.
4. Add tests + an entry in the relevant eval dataset if it affects tool selection.

### Add / tighten an eval

1. Add rows to a dataset in `src/aih/evals/datasets/*.jsonl`.
2. Adjust thresholds in `src/aih/evals/thresholds.json` (raising a bar is encouraged; lowering
   one needs justification in the PR).
3. Run `python tasks.py eval` and confirm the scorecard.

## Commit & PR conventions

- Small, focused commits. Reference the spec id where relevant.
- Use conventional prefixes where they fit: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
- PRs should describe **what** changed and **why**, and note any spec/threshold changes.
- Do not commit generated artifacts (coverage DBs, build caches, `node_modules/`) — they're gitignored.

## Reporting bugs / requesting features

Open an issue using the templates. For anything security-related, see [`SECURITY.md`](SECURITY.md).
