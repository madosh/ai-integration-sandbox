# System design drill 2 — Add HITL to an agent safely

**Time:** 20 min

## Prompt

An agent can call tools that push creatives and modify campaigns. How do you add human-in-the-loop
without blocking the whole system?

<details>
<summary>Model answer</summary>

**Gate side effects:** classify tools/skills with `side_effect: bool`; read-only runs fully automated.

**Approval envelope:** side-effecting MCP tools return `requires_approval` with payload preview;
agent pauses at `ApprovalRequest` until `APIApprover` / SQS message resolved.

**Durability:** SQS queue for cross-process approvals; visibility timeout + DLQ for stuck items.

**Audit:** log every decision to run ledger with who/when/why.

**Deny path:** no tool execution; agent observes denial and may replan.

**UX:** dashboard Approve/Deny wired to `POST /runs/{id}/approve`.

</details>
