# Security Policy

## Scope

This is an **offline-first sandbox** intended for local development, learning, and interview
rehearsal. By default it uses deterministic fakes and local mock APIs — it ships with **no real
credentials** and makes no outbound calls unless you explicitly opt into a real provider.

## Reporting a vulnerability

If you find a security issue (for example: a way the HITL approval gate can be bypassed, an
injection that defeats the RAG safety filter, or a secret-handling problem in a real-provider
code path), please report it privately:

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on this repository, **or**
- Open a minimal issue asking for a private channel — do **not** include exploit details in a
  public issue.

Please include reproduction steps and the affected module. We aim to acknowledge reports within a
few days.

## Good to know

- Never commit real API keys. Use environment variables (see `.env.example`); `.env` is gitignored.
- Real adapters (e.g. `anthropic`, OTel exporters) are optional extras and disabled by default.
