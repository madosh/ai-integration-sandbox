"""Query rewriting / expansion for better retrieval."""

from __future__ import annotations

import re

_SYNONYMS = {
    "429": "rate limit retry-after",
    "pagination": "cursor offset limit page",
    "creative": "multipart upload file",
    "auth": "bearer api-key basic authentication",
}


def rewrite_query(query: str) -> str:
    """Deterministic query expansion (offline HyDE-lite)."""
    extra: list[str] = []
    lower = query.lower()
    for key, expansion in _SYNONYMS.items():
        if key in lower:
            extra.append(expansion)
    if not extra:
        return query
    return query + " " + " ".join(extra)


def decompose_query(query: str) -> list[str]:
    """Split compound questions on ' and ' for multi-hop-style retrieval."""
    parts = re.split(r"\s+and\s+", query, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()] if len(parts) > 1 else [query]
