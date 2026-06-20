# ADR 001: SQS for human-in-the-loop approval queue

## Status

Accepted

## Context

Side-effecting agent steps (creative upload, campaign publish) require human approval before
execution. Approvals can arrive from the dashboard, CLI, or an external ticketing workflow. We need
decoupling between the agent process (which may block) and approvers (which are asynchronous).

## Decision

Use **Amazon SQS** (LocalStack in dev) as the durable approval queue:

- Agent emits an approval request message with run id, action, payload preview.
- Approvers consume via API/dashboard; resolution is published back (or the API resolves the in-process
  `APIApprover` gate directly for the MVP).
- SQS provides at-least-once delivery, visibility timeout, and dead-letter queue support for stuck approvals.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| In-process only (`APIApprover`) | Simple for MVP but no cross-process durability |
| Redis pub/sub | Fast but less durable; ops burden for persistence |
| Step Functions wait task | Heavy for a small hub; vendor lock-in on workflow shape |
| Database polling | Works but couples approval latency to DB poll interval |

## Consequences

- **Positive:** Durable, scalable approval backlog; familiar AWS ops patterns.
- **Negative:** Extra infrastructure; LocalStack parity gaps for advanced SQS features.
