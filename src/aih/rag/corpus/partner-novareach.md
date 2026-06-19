# NovaReach Partner Specification

NovaReach authenticates with an API key passed in the X-API-Key header. The campaigns endpoint uses
offset and limit pagination, returning a records array together with a total count so the client
knows when to stop. Budgets are reported as floating point currency amounts and impressions are the
primary volume metric. NovaReach also accepts campaign creation via POST with an idempotency key to
avoid duplicate writes.
