"""The deterministic policy gate.

Plain Python, no model calls. Maps a ``(finding, judge proposal)`` pair to a final
:class:`Disposition`, enforcing the safety invariants that keep a fallible judge from ever
auto-closing a real security finding. The gate can only make a proposal *more* cautious —
it never introduces a ``dismiss``.
"""

from __future__ import annotations

from pydantic import BaseModel

from aih.adjudication.models import Disposition, Finding, JudgeProposal, Severity


class PolicyConfig(BaseModel):
    """Tunable definition of what counts as "consequential" (SPEC decision D6)."""

    escalate_types: frozenset[str] = frozenset({"vulnerability", "security_hotspot"})
    escalate_severities: frozenset[Severity] = frozenset({"critical", "blocker"})


def is_consequential(finding: Finding, config: PolicyConfig) -> bool:
    """A finding is consequential if its type or severity makes an auto-dismiss unsafe."""
    return (
        finding.finding_type in config.escalate_types
        or finding.severity in config.escalate_severities
    )


def apply_policy(
    finding: Finding,
    proposal: JudgeProposal | None,
    config: PolicyConfig | None = None,
) -> Disposition:
    """Return the final disposition for ``finding`` given the judge's ``proposal``."""
    config = config or PolicyConfig()

    # No proposal at all (judge failed / absent) → fail safe toward a human.
    if proposal is None:
        return Disposition(
            action="escalate",
            routed_to="human_queue",
            overridden=True,
            reason="no judge proposal; escalating",
        )

    # Distrust a proposal that does not round-trip the finding it claims to be about.
    if proposal.finding_key != finding.key or proposal.rule != finding.rule:
        return Disposition(
            action="escalate",
            routed_to="human_queue",
            overridden=True,
            reason="proposal finding_key/rule does not match the finding; distrusted",
        )

    if proposal.action == "dismiss":
        return _gate_dismissal(finding, proposal, config)

    if proposal.action == "confirm":
        return Disposition(action="confirm", routed_to="auto", reason="finding confirmed")

    # escalate
    return Disposition(action="escalate", routed_to="human_queue", reason="judge escalated")


def _gate_dismissal(finding: Finding, proposal: JudgeProposal, config: PolicyConfig) -> Disposition:
    """A dismissal is the only restricted action. Apply the two override rules."""
    if not proposal.evidence:
        return Disposition(
            action="escalate",
            routed_to="human_queue",
            overridden=True,
            reason="dismissal has no supporting evidence; auto-escalated",
        )
    if is_consequential(finding, config):
        return Disposition(
            action="escalate",
            routed_to="human_queue",
            overridden=True,
            reason=(
                "never auto-close a consequential finding "
                f"({finding.finding_type}/{finding.severity}); escalated"
            ),
        )
    return Disposition(
        action="dismiss",
        routed_to="auto",
        reason="low-risk finding dismissed with evidence",
    )
