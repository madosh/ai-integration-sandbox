# Spec: agent — orchestrator + human-in-the-loop

## Goal

Given a goal, plan and execute a sequence of skills/tools with a bounded step budget, a full,
inspectable run trace, and a human-in-the-loop gate on any side-effecting step. This is the Factorial
agentic-workflow + HITL surface.

## Inputs / Outputs

- **Input:** a natural-language `goal`, an injected `Approver`, a `SkillRegistry`, an `LLMClient`
  (FakeLLM by default), and a `RunLedger`.
- **Output:** a `RunResult` containing the final output and a `RunTrace` (ordered `RunStep`s:
  plan / skill / approval / observation / finish / error), persisted to the ledger.

## Behaviour

1. The planner builds real `ToolSpec`s from each skill's input schema plus a `finish` tool and asks
   the `LLMClient` to select a tool via `tool_call` (function-calling style).
2. The loop: select -> (gate if side-effecting) -> execute -> observe -> iterate, up to
   `agent_max_steps`. It converges (stops) when the planner re-selects the same tool+args or selects
   `finish`.
3. Side-effecting skills pause at the approval gate: a structured `ApprovalRequest` (what / why /
   payload preview / reversibility) is sent to the `Approver`. The skill runs ONLY if
   `decision.approved` is true; a denial records the decision and performs no side effect.
4. Every approval decision and step is recorded to the run ledger; the trace is fully inspectable.
5. Approvers provided: `AutoApprover` (programmatic/tests), `CLIApprover` (stdin), and `APIApprover`
   (await an external resolution; used by the service in Phase 6).

## Constraints

- Deterministic under FakeLLM. Bounded steps (`agent_max_steps`). The planner prompt and tool schemas
  are real (an interviewer will probe them).
- No side effect occurs without an explicit approve.

## Failure modes

- Unknown tool selected -> error step, loop continues/converges.
- Invalid args -> error step.
- Step budget exhausted -> `status="max_steps"`, trace still returned.

## Success criteria (measurable)

- E2E: goal "publish the new creative to NovaReach" -> the agent plans, hits the approval gate, and
  uploads ONLY when `approved=true`. A denial leaves NO creative stored on the mock API.
- The run trace contains a plan/selection, an approval step with the decision, and the skill result.
- `answer_from_docs` via the agent returns a cited answer.

## Out of scope

- Parallel tool execution, multi-agent orchestration, retries/replanning on skill failure,
  persistent durable workflow resumption (the ledger persists traces; resumable execution is not
  implemented).
