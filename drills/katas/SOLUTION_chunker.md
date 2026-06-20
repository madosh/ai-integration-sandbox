# Kata 3 — Token chunker

Slide window: start at 0, take `chunk_size`, next start += `chunk_size - overlap`.

<details>
<summary>Model answer</summary>

```python
def chunk_tokens(tokens, chunk_size, overlap):
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size")
    chunks = []
    start = 0
    while start < len(tokens):
        chunks.append(tokens[start:start + chunk_size])
        if start + chunk_size >= len(tokens):
            break
        start += chunk_size - overlap
    return chunks
```

</details>
