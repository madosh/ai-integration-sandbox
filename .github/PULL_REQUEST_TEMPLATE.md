## Summary

What does this PR change, and why?

## Related spec

Link the spec in `specs/` this implements or updates (spec-before-code is required for features).

## Checklist

- [ ] Spec added/updated in `specs/` (for features)
- [ ] Stays offline-first (works with `FakeLLM` / `HashEmbedder` / `mock_apis/`; real providers opt-in)
- [ ] Side-effecting skills route through the HITL approval gate
- [ ] `python tasks.py lint` passes
- [ ] `python tasks.py type` passes
- [ ] `python tasks.py test` passes (coverage ≥ 70%)
- [ ] `python tasks.py eval` passes (no metric below `src/aih/evals/thresholds.json`)
- [ ] No generated artifacts committed (coverage DBs, build caches, `node_modules/`)

## Notes for reviewers

Anything that needs extra attention (threshold changes, new deps, migrations).
