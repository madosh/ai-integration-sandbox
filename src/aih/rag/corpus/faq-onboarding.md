# Onboarding FAQ: Adding a New Partner

How do I onboard a new partner network? The integration framework is built around connectors that are
discoverable through a registry. To add a new partner you write one connector module that maps the
partner payloads onto the normalized campaign model, then register it by name in the registry. No core
code changes are required. Each connector reuses the shared transport, so retries, backoff, timeouts,
and structured logging come for free. Reusable capabilities are exposed as skills that the agent can
invoke and that can be tested in isolation.
