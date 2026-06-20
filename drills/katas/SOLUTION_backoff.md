# Kata 1 — Backoff + jitter retry decorator

Implement `retry_with_backoff` in `backoff.py`:

- Retry on any exception until `max_attempts`.
- Delay = `base_delay * 2 ** (attempt - 1)` plus uniform jitter in `[0, jitter]`.
- Use `asyncio.sleep` between attempts.

<details>
<summary>Model answer</summary>

```python
import asyncio
import random

def retry_with_backoff(max_attempts=3, base_delay=0.1, jitter=0.1):
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, jitter)
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

</details>
