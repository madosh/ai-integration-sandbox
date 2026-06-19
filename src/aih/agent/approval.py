"""Human-in-the-loop approval primitives + approvers.

The data models are shared by the MCP layer (which emits ``requires_approval``
envelopes for side-effecting tools) and the agent layer (which enforces the gate).
This module also provides the approver implementations: programmatic, CLI, and an
API-backed approver that awaits an external resolution.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Reversibility = Literal["low", "medium", "high"]


class ApprovalRequest(BaseModel):
    """A structured request for human sign-off before a side effect runs."""

    action: str  # what (e.g. "push_creative")
    connector: str | None = None
    summary: str  # why / human-readable description
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    reversibility: Reversibility = "low"
    run_id: str | None = None


class ApprovalDecision(BaseModel):
    """The resolution of an approval request."""

    approved: bool
    decided_by: str = "unknown"
    reason: str | None = None


@runtime_checkable
class Approver(Protocol):
    """Resolve an approval request to a decision."""

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        """Return the human (or policy) decision for ``request``."""
        ...


class AutoApprover:
    """Resolve every request the same way (tests / fully-automated pipelines)."""

    def __init__(self, approved: bool, *, decided_by: str = "auto", reason: str | None = None):
        self._approved = approved
        self._decided_by = decided_by
        self._reason = reason

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(
            approved=self._approved, decided_by=self._decided_by, reason=self._reason
        )


class CLIApprover:
    """Prompt a human on stdin (for local CLI runs)."""

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        print("\n=== APPROVAL REQUIRED ===")
        print(f"action:        {request.action}")
        print(f"connector:     {request.connector}")
        print(f"summary:       {request.summary}")
        print(f"reversibility: {request.reversibility}")
        print(f"payload:       {request.payload_preview}")
        answer = (await asyncio.to_thread(input, "approve? [y/N]: ")).strip().lower()
        return ApprovalDecision(approved=answer in {"y", "yes"}, decided_by="cli")


class APIApprover:
    """Await an external resolution (used by the FastAPI service in Phase 6).

    The agent calls :meth:`decide`, which parks a pending request keyed by run id
    and blocks until :meth:`resolve` is called (e.g. from a ``POST /runs/{id}/approve``
    handler or a dashboard button).
    """

    def __init__(self) -> None:
        self._pending: dict[str, tuple[ApprovalRequest, asyncio.Future[ApprovalDecision]]] = {}

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        key = request.run_id or request.action
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ApprovalDecision] = loop.create_future()
        self._pending[key] = (request, future)
        try:
            return await future
        finally:
            self._pending.pop(key, None)

    def pending(self) -> dict[str, ApprovalRequest]:
        return {k: req for k, (req, _) in self._pending.items()}

    def get_pending(self, key: str) -> ApprovalRequest | None:
        entry = self._pending.get(key)
        return entry[0] if entry else None

    def resolve(self, key: str, *, approved: bool, decided_by: str = "api") -> bool:
        """Resolve a pending request. Returns True if a request was waiting."""
        entry = self._pending.get(key)
        if entry is None:
            return False
        _, future = entry
        if not future.done():
            future.set_result(ApprovalDecision(approved=approved, decided_by=decided_by))
        return True
