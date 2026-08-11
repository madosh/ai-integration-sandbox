"""Pydantic v2 contracts for the adjudication layer.

These models are the safety boundary. The design goal is to make unsafe states
*unrepresentable*: a dismissal with no supporting evidence cannot even be constructed
(:class:`Verdict` raises), and every proposal must round-trip the finding it refers to.

Nothing here calls a model or the network — this is pure schema + validation.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

Severity = Literal["info", "minor", "major", "critical", "blocker"]
FindingType = Literal["bug", "vulnerability", "code_smell", "security_hotspot"]
Action = Literal["confirm", "dismiss", "escalate"]
RoutedTo = Literal["auto", "human_queue"]


class Finding(BaseModel):
    """A static-analysis finding to adjudicate (SonarQube-style).

    ``key`` and ``rule`` are the identity of the finding and must round-trip through
    serialization unchanged — everything downstream keys off them.
    """

    model_config = {"frozen": True}

    key: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    severity: Severity
    finding_type: FindingType
    message: str = ""
    file_path: str = Field(min_length=1)
    line: int = Field(ge=1)
    # Present for hotspots; None for ordinary issues.
    status: str | None = None


class EvidenceSpan(BaseModel):
    """A window of source lines gathered as evidence for a finding.

    ``text`` is untrusted input: it is code and comments, treated as data, never as
    instructions to the judge or the gate.
    """

    model_config = {"frozen": True}

    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    text: str

    @model_validator(mode="after")
    def _check_range(self) -> EvidenceSpan:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class JudgeProposal(BaseModel):
    """What the judge returns *before* the deterministic policy gate.

    ``evidence`` holds indices into the gathered spans that justify the action. The
    ``finding_key``/``rule`` must match the finding under review; a mismatch is distrusted
    by the gate.
    """

    action: Action
    rationale: str = ""
    evidence: list[int] = Field(default_factory=list)
    finding_key: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Verdict(BaseModel):
    """The safety-bearing verdict schema.

    A ``dismiss`` with an empty ``evidence`` list is rejected at construction time: silently
    dropping a finding with no justification is not a representable state. This is enforced in
    the type, not merely checked downstream (SPEC decision D4).
    """

    action: Action
    finding_key: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    rationale: str = ""

    @model_validator(mode="after")
    def _no_unjustified_dismissal(self) -> Verdict:
        if self.action == "dismiss" and not self.evidence:
            raise ValueError(
                "a 'dismiss' verdict requires non-empty evidence (auto-escalate instead)"
            )
        return self


class Disposition(BaseModel):
    """The deterministic policy gate's output for a finding."""

    action: Action
    routed_to: RoutedTo
    overridden: bool = False
    reason: str = ""


class AuditEntry(BaseModel):
    """One append-only, hash-chained audit record.

    ``entry_hash`` is computed over the entry's content plus ``prev_hash``; a break in the
    chain makes tampering detectable (SPEC decision D5).
    """

    finding_key: str
    rule: str
    proposed_action: Action
    final_action: Action
    routed_to: RoutedTo
    overridden: bool
    reason: str
    evidence_digest: str
    prev_hash: str
    entry_hash: str
    ts: float = Field(default_factory=time.time)


class AdjudicationResult(BaseModel):
    """The full, inspectable result of adjudicating one finding.

    ``verdict`` is the safety-bearing record for auto-decided dispositions (confirm / dismiss).
    Because it is a :class:`Verdict`, a dismiss on this path is *guaranteed* to carry evidence —
    the contract is on the real output, not just a standalone schema. It is ``None`` for
    escalations (a human, not the schema, owns those).
    """

    finding: Finding
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    proposal: JudgeProposal | None = None
    disposition: Disposition
    verdict: Verdict | None = None
    error: str | None = None
