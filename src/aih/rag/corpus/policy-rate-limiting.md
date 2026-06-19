# Rate Limiting and Retry Policy

All partner integrations must respect upstream rate limits. When a partner responds with HTTP 429,
the client must read the Retry-After header and wait before retrying. Retries use exponential backoff
with jitter and are bounded by a maximum attempt budget. Server errors (HTTP 5xx) and transient
network failures are also retried with backoff. A circuit breaker opens after repeated consecutive
failures and fails fast until a cooldown period elapses, protecting the pipeline from a flaky partner.
