"""RAG safety: injection patterns and context hardening."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+the\s+context",
    r"system\s*:",
    r"<\s*script",
]


def detect_injection(text: str) -> bool:
    """Return True if text looks like a prompt-injection attempt."""
    lower = text.lower()
    return any(re.search(p, lower) for p in _INJECTION_PATTERNS)


def sanitize_query(query: str) -> str:
    """Strip obvious injection phrases from user queries."""
    out = query
    for pat in _INJECTION_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    return out.strip() or query


def wrap_context(chunks: list[str]) -> str:
    """Delimiter-wrapped context block for grounded generation."""
    body = "\n---\n".join(chunks)
    return f"<<TRUSTED_CONTEXT>>\n{body}\n<<END_CONTEXT>>"
