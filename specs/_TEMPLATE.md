# Spec: <feature-id> — <short title>

> Spec-Driven Development template. Copy this file to `specs/<feature>.md` and fill in every section
> BEFORE writing code. Reference the spec id (e.g. `connectors`) in the commit message.

## Goal

What problem does this solve, and for whom? One or two sentences.

## Inputs / Outputs

- **Inputs:** data, types, sources (cite Pydantic models where relevant).
- **Outputs:** data, types, side effects.

## Behaviour

The happy-path flow, step by step. Reference functions/modules by name.

## Constraints

Non-functional requirements: performance, offline-first, type-safety, idempotency, security, etc.

## Failure modes

What can go wrong and how the system responds (errors, retries, fallbacks, degraded modes).

## Success criteria (measurable)

Concrete, testable assertions. Each should map to a test. e.g. "pagination iterates >1 page",
"forced 429 retries and succeeds", "metric X >= threshold".

## Out of scope

Explicitly what this feature does NOT cover, to bound the work.
