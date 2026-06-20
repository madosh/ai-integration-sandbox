# Kata 5 — Idempotent push

Track seen idempotency keys; second call with same key returns `duplicate` without calling `push_fn`.

<details>
<summary>Model answer</summary>

```python
async def push_once(self, key, push_fn, payload):
    if key in self._seen:
        return "duplicate"
    self._seen.add(key)
    await push_fn(payload)
    return "pushed"
```

</details>
