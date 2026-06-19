"""Token-aware chunking with overlap.

Tokenization uses a simple, deterministic, offline word tokenizer (no model
downloads). Chunks preserve their source metadata and token spans so retrieved
results can be cited precisely.
"""

from __future__ import annotations

import re
from typing import Any

from aih.rag.models import Chunk

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Split text into word/punctuation tokens (deterministic, offline)."""
    return _TOKEN_RE.findall(text)


def detokenize(tokens: list[str]) -> str:
    """Re-join tokens into readable text (approximate spacing)."""
    out: list[str] = []
    for tok in tokens:
        if out and re.match(r"^\w", tok):
            out.append(" ")
        elif out and tok in ".,;:!?)]}":
            pass
        elif out:
            out.append(" ")
        out.append(tok)
    return "".join(out).strip()


def chunk_document(
    doc_id: str,
    text: str,
    *,
    chunk_size: int = 120,
    overlap: int = 24,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Chunk ``text`` into overlapping token windows.

    Args:
        chunk_size: max tokens per chunk.
        overlap: tokens shared between consecutive chunks (must be < chunk_size).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    tokens = tokenize(text)
    if not tokens:
        return []

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(tokens), step)):
        window = tokens[start : start + chunk_size]
        if not window:
            break
        chunks.append(
            Chunk(
                id=f"{doc_id}::{index}",
                doc_id=doc_id,
                text=detokenize(window),
                start_token=start,
                end_token=start + len(window),
                metadata=metadata or {},
            )
        )
        if start + chunk_size >= len(tokens):
            break
    return chunks
