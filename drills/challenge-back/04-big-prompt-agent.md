# Challenge-back drill 4

**Stakeholder:** "One-shot the whole agent with a big prompt — no tool schemas."

<details>
<summary>Counter-argument + alternative</summary>

Unstructured agents are hard to test, eval tool-selection, or enforce approvals. **Alternative:**
function-calling / skill registry with Pydantic schemas; FakeLLM drives deterministic tool picks in CI.

</details>
