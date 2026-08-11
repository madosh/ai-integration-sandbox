"""The judge: the *only* node permitted to reason over evidence.

The default :class:`RuleBasedJudge` is deterministic and makes **no** model call and **no**
network call, so it is what the whole test suite uses. A real judge (Bedrock / Vertex /
Anthropic) implements the same :class:`Judge` protocol behind an optional extra and is never
imported on the test path.

Security property: the judge's action is a function of the finding's *structured metadata*, not
of directives embedded in the source. Code and comments are data. As defence in depth, if the
gathered evidence contains prompt-injection phrasing, the judge refuses to dismiss and escalates
instead. A comment that says "mark this SAFE" can never turn into an auto-dismissal.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aih.adjudication.models import Action, EvidenceSpan, Finding, JudgeProposal

# Phrases that indicate the source is trying to steer the verdict. Matched as data; their only
# effect is to make the judge *more* cautious (escalate), never less.
INJECTION_MARKERS: tuple[str, ...] = (
    "mark this safe",
    "mark as safe",
    "ignore previous",
    "ignore all previous",
    "dismiss this",
    "this is safe, dismiss",
    "please dismiss",
    "you are now",
    "override the",
    "as an ai",
)


@runtime_checkable
class Judge(Protocol):
    """Propose a verdict for a finding, given gathered evidence."""

    def propose(self, finding: Finding, evidence: list[EvidenceSpan]) -> JudgeProposal:
        """Return a :class:`JudgeProposal`. Must not raise on ordinary inputs."""
        ...


def _looks_like_injection(evidence: list[EvidenceSpan]) -> bool:
    joined = "\n".join(span.text for span in evidence).lower()
    return any(marker in joined for marker in INJECTION_MARKERS)


class RuleBasedJudge:
    """Deterministic, offline judge driven by finding metadata (not source directives).

    Policy:

    - ``vulnerability`` / ``security_hotspot`` — never dismissed. ``confirm`` when the severity
      is at least ``major``, otherwise ``escalate``.
    - ``bug`` — ``confirm`` (real defects are kept).
    - ``code_smell`` — ``dismiss`` (with the span cited as evidence) only for ``info``/``minor``
      severity *and* only when the evidence shows no injection phrasing; otherwise ``escalate``.
    """

    def propose(self, finding: Finding, evidence: list[EvidenceSpan]) -> JudgeProposal:
        injected = _looks_like_injection(evidence)
        cited = [0] if evidence else []

        action: Action = self._decide(finding, has_evidence=bool(evidence), injected=injected)

        # A dismiss must cite evidence (else the Verdict contract / gate rejects it). By
        # construction we only reach dismiss when evidence exists, but guard anyway.
        if action == "dismiss" and not cited:
            action = "escalate"

        rationale = self._rationale(finding, action, injected=injected)
        confidence = self._confidence(finding, action)
        return JudgeProposal(
            action=action,
            rationale=rationale,
            evidence=cited if action != "escalate" else [],
            finding_key=finding.key,
            rule=finding.rule,
            confidence=confidence,
        )

    @staticmethod
    def _decide(finding: Finding, *, has_evidence: bool, injected: bool) -> Action:
        if finding.finding_type in {"vulnerability", "security_hotspot"}:
            if finding.severity in {"major", "critical", "blocker"}:
                return "confirm"
            return "escalate"
        if finding.finding_type == "bug":
            return "confirm"
        # code_smell
        if finding.severity in {"info", "minor"} and has_evidence and not injected:
            return "dismiss"
        return "escalate"

    @staticmethod
    def _rationale(finding: Finding, action: Action, *, injected: bool) -> str:
        # Rationale is templated from metadata only — never echoes source content.
        if injected and action == "escalate":
            return (
                f"evidence for {finding.rule} contains verdict-steering phrasing; "
                "escalating rather than trusting in-source directives"
            )
        base = {
            "confirm": f"{finding.finding_type} '{finding.rule}' at {finding.severity} kept as a "
            "true positive",
            "dismiss": f"low-severity {finding.finding_type} '{finding.rule}' assessed as a "
            "likely false positive",
            "escalate": f"{finding.finding_type} '{finding.rule}' is not safely auto-decidable",
        }
        return base[action]

    @staticmethod
    def _confidence(finding: Finding, action: Action) -> float:
        if action == "escalate":
            return 0.3
        if finding.severity in {"critical", "blocker"}:
            return 0.9
        if finding.severity == "major":
            return 0.75
        return 0.6
