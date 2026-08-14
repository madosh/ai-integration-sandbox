"""The deterministic policy gate: the safety invariants that keep the judge out of control."""

from __future__ import annotations

import pytest

from aih.adjudication import (
    Disposition,
    Finding,
    JudgeProposal,
    PolicyConfig,
    apply_policy,
    is_consequential,
)


def _finding(**over: object) -> Finding:
    base: dict[str, object] = {
        "key": "K1",
        "rule": "R1",
        "severity": "minor",
        "finding_type": "code_smell",
        "file_path": "a.py",
        "line": 3,
    }
    base.update(over)
    return Finding.model_validate(base)


def _dismiss(finding: Finding, *, evidence: list[int] | None = None) -> JudgeProposal:
    return JudgeProposal(
        action="dismiss",
        finding_key=finding.key,
        rule=finding.rule,
        evidence=[0] if evidence is None else evidence,
    )


@pytest.mark.parametrize(
    ("finding_type", "severity"),
    [
        ("vulnerability", "minor"),
        ("security_hotspot", "minor"),
        ("code_smell", "critical"),
        ("bug", "blocker"),
    ],
)
def test_consequential_dismissal_is_overridden_to_escalate(
    finding_type: str, severity: str
) -> None:
    finding = _finding(finding_type=finding_type, severity=severity)
    disp = apply_policy(finding, _dismiss(finding))
    assert disp.action == "escalate"
    assert disp.routed_to == "human_queue"
    assert disp.overridden is True


def test_low_risk_dismissal_with_evidence_is_allowed() -> None:
    finding = _finding(finding_type="code_smell", severity="minor")
    disp = apply_policy(finding, _dismiss(finding))
    assert disp == Disposition(
        action="dismiss", routed_to="auto", overridden=False, reason=disp.reason
    )
    assert disp.action == "dismiss"
    assert disp.overridden is False


def test_dismissal_without_evidence_auto_escalates() -> None:
    finding = _finding(finding_type="code_smell", severity="minor")
    disp = apply_policy(finding, _dismiss(finding, evidence=[]))
    assert disp.action == "escalate"
    assert disp.overridden is True


def test_confirm_is_auto_routed() -> None:
    finding = _finding(finding_type="vulnerability", severity="blocker")
    proposal = JudgeProposal(action="confirm", finding_key=finding.key, rule=finding.rule)
    disp = apply_policy(finding, proposal)
    assert disp.action == "confirm"
    assert disp.routed_to == "auto"
    assert disp.overridden is False


def test_escalate_goes_to_human_queue() -> None:
    finding = _finding()
    proposal = JudgeProposal(action="escalate", finding_key=finding.key, rule=finding.rule)
    disp = apply_policy(finding, proposal)
    assert disp.action == "escalate"
    assert disp.routed_to == "human_queue"


def test_mismatched_key_or_rule_is_distrusted() -> None:
    finding = _finding()
    bad_key = JudgeProposal(action="confirm", finding_key="OTHER", rule=finding.rule)
    bad_rule = JudgeProposal(action="dismiss", finding_key=finding.key, rule="OTHER", evidence=[0])
    for proposal in (bad_key, bad_rule):
        disp = apply_policy(finding, proposal)
        assert disp.action == "escalate"
        assert disp.overridden is True


def test_missing_proposal_fails_safe() -> None:
    disp = apply_policy(_finding(), None)
    assert disp.action == "escalate"
    assert disp.overridden is True


def test_gate_never_introduces_a_dismiss() -> None:
    # A confirm/escalate proposal can never come out of the gate as a dismiss.
    finding = _finding(finding_type="code_smell", severity="info")
    for action in ("confirm", "escalate"):
        proposal = JudgeProposal(action=action, finding_key=finding.key, rule=finding.rule)
        assert apply_policy(finding, proposal).action != "dismiss"


def test_is_consequential_matches_config() -> None:
    cfg = PolicyConfig()
    assert is_consequential(_finding(finding_type="vulnerability", severity="info"), cfg)
    assert is_consequential(_finding(finding_type="code_smell", severity="blocker"), cfg)
    assert not is_consequential(_finding(finding_type="code_smell", severity="minor"), cfg)
