"""End-to-end: the state machine over packaged fixtures."""

from __future__ import annotations

from aih.adjudication import (
    AuditLog,
    Finding,
    FixtureSource,
    HumanQueue,
    run_batch,
    run_pipeline,
)


def _finding(**over: object) -> Finding:
    base: dict[str, object] = {
        "key": "K1",
        "rule": "R1",
        "severity": "blocker",
        "finding_type": "vulnerability",
        "file_path": "payments/checkout.py",
        "line": 3,
    }
    base.update(over)
    return Finding.model_validate(base)


def test_single_finding_confirms_vulnerability() -> None:
    result = run_pipeline(_finding(), source=FixtureSource())
    assert result.disposition.action == "confirm"
    assert result.disposition.routed_to == "auto"
    assert result.proposal is not None
    assert result.evidence  # evidence was gathered from the fixture
    assert result.error is None
    # Auto-decided → a safety-checked Verdict is on the result.
    assert result.verdict is not None
    assert result.verdict.action == "confirm"


def test_auto_dismiss_carries_a_verdict_with_evidence() -> None:
    result = run_pipeline(
        _finding(finding_type="code_smell", severity="minor", file_path="utils/format.py", line=5),
        source=FixtureSource(),
    )
    assert result.disposition.action == "dismiss"
    assert result.verdict is not None
    assert result.verdict.action == "dismiss"
    assert result.verdict.evidence  # the Verdict contract guarantees this on the dismiss path


def test_escalation_has_no_verdict() -> None:
    result = run_pipeline(
        _finding(
            finding_type="security_hotspot", severity="minor", file_path="auth/login.py", line=10
        ),
        source=FixtureSource(),
    )
    assert result.disposition.action == "escalate"
    assert result.verdict is None  # humans own escalations, not the schema


def test_missing_file_yields_no_evidence_and_never_dismisses() -> None:
    result = run_pipeline(
        _finding(finding_type="code_smell", severity="minor", file_path="does/not/exist.py"),
        source=FixtureSource(),
    )
    assert result.evidence == []
    assert result.disposition.action != "dismiss"


def test_batch_shares_audit_and_queue() -> None:
    findings = [
        _finding(key="V1", finding_type="vulnerability", severity="blocker"),
        _finding(
            key="B1",
            finding_type="bug",
            severity="major",
            file_path="orders/process.py",
            line=5,
        ),
        _finding(
            key="S1",
            finding_type="code_smell",
            severity="minor",
            file_path="utils/format.py",
            line=5,
        ),
        _finding(
            key="H1",
            finding_type="security_hotspot",
            severity="minor",
            file_path="auth/login.py",
            line=10,
        ),
    ]
    audit = AuditLog()
    queue = HumanQueue()
    results = run_batch(findings, source=FixtureSource(), audit=audit, queue=queue)

    assert len(results) == len(findings)
    # One audit entry per finding, chain intact.
    assert len(audit.entries) == len(findings)
    assert audit.verify() is True
    # Everything routed to the human queue is exactly the escalations.
    escalated = [r for r in results if r.disposition.routed_to == "human_queue"]
    assert len(queue) == len(escalated)
    # The low-severity hotspot is not auto-decidable → escalates (never dismissed).
    hotspot = next(r for r in results if r.finding.key == "H1")
    assert hotspot.disposition.action == "escalate"
