# Kata 6 — Token bucket

Refill tokens at `rate` per second up to `capacity`; `acquire` blocks until a token is available.

<details>
<summary>Model answer</summary>

Use `asyncio.Lock`, track `tokens` and `last_refill` time; on acquire refill based on elapsed time, sleep if empty.

</details>
