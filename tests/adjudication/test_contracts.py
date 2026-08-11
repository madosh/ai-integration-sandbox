"""Pydantic contract tests: unsafe states must be unrepresentable, identity must round-trip."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aih.adjudication import EvidenceSpan, Finding, JudgeProposal, Verdict


def _span() -> EvidenceSpan:
    return EvidenceSpan(file_path="a.py", start_line=1, end_line=3, text="x = 1")


def test_dismiss_with_empty_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Verdict(action="dismiss", finding_key="K1", rule="R1", evidence=[])


def test_dismiss_with_evidence_is_allowed() -> None:
    verdict = Verdict(action="dismiss", finding_key="K1", rule="R1", evidence=[_span()])
    assert verdict.action == "dismiss"


def test_escalate_and_confirm_need_no_evidence() -> None:
    assert Verdict(action="escalate", finding_key="K1", rule="R1").evidence == []
    assert Verdict(action="confirm", finding_key="K1", rule="R1").evidence == []


def test_finding_key_and_rule_round_trip() -> None:
    finding = Finding(
        key="AY-42",
        rule="python:S3649",
        severity="major",
        finding_type="security_hotspot",
        file_path="auth/login.py",
        line=10,
    )
    restored = Finding.model_validate(finding.model_dump())
    assert restored.key == "AY-42"
    assert restored.rule == "python:S3649"
    assert restored == finding


def test_finding_rejects_zero_line() -> None:
    with pytest.raises(ValidationError):
        Finding(
            key="K",
            rule="R",
            severity="minor",
            finding_type="code_smell",
            file_path="a.py",
            line=0,
        )


def test_proposal_requires_key_and_rule() -> None:
    with pytest.raises(ValidationError):
        JudgeProposal(action="confirm", finding_key="", rule="R1")


def test_evidence_span_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        EvidenceSpan(file_path="a.py", start_line=5, end_line=2, text="")
