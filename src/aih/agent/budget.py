"""Token budget enforcement for agent loops."""

from __future__ import annotations

from aih.config import get_settings


class TokenBudget:
    """Simple token budget counter (estimated tokens, offline)."""

    def __init__(self, limit: int | None = None) -> None:
        self.limit = limit or get_settings().agent_token_budget
        self.used = 0

    def charge(self, tokens: int) -> bool:
        """Add tokens; return False if budget exceeded."""
        self.used += tokens
        return self.used <= self.limit

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def exhausted(self) -> bool:
        return self.used > self.limit
