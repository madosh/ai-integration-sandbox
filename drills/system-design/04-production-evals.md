# System design drill 4 — Eval strategy for a production agent

**Time:** 20 min

## Prompt

How do you evaluate an integration agent in production without burning budget or risking side effects?

<details>
<summary>Model answer</summary>

**Layers:**

1. **Unit/offline:** FakeLLM + mock APIs; tool-selection accuracy, retrieval metrics, rubric judges.
2. **Regression CI:** committed thresholds in `thresholds.json`; fail build on drop.
3. **Shadow/read-only:** run planner against prod traffic logs with side effects disabled.
4. **HITL sampling:** export review queue for generative answers; fold labels back.
5. **Production monitors:** success rate, approval rate, connector error codes, latency — not a substitute for golden evals.

**Trust automated for:** retrieval, structured tool pick, exact match tasks.
**Trust humans for:** open-ended generation, policy interpretation, new partner onboarding.

</details>
