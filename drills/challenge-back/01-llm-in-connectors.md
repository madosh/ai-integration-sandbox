# Challenge-back drill 1

**Stakeholder:** "Let's call the LLM directly from each connector — it's simpler."

<details>
<summary>Counter-argument + alternative</summary>

Direct LLM calls in connectors couple networking, auth, and AI policy in one place — untestable,
unreusable, and hard to eval. **Alternative:** connectors stay deterministic REST; LLM lives in
skills/agent with typed I/O and FakeLLM for tests.

</details>
