---
name: Feature request
about: Propose a new capability or enhancement
title: "feat: "
labels: enhancement
---

## Problem / motivation

What are you trying to do, and why is it hard today?

## Proposed solution

What you'd like to see. If it's a new feature, note that it will need a spec in
`specs/<feature>.md` before implementation.

## Offline-first check

- [ ] This works with `FakeLLM` / `HashEmbedder` / `mock_apis/` (real providers stay opt-in)
- [ ] Side-effecting behaviour (if any) routes through the HITL approval gate

## Alternatives considered

Any other approaches you weighed.
