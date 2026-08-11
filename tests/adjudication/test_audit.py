"""The hash-chained audit log: append-only, tamper-evident, persistable."""

from __future__ import annotations

from pathlib import Path

from aih.adjudication import AuditLog, Disposition, Finding, JudgeProposal
from aih.adjudication.audit import GENESIS_HASH


def _finding(key: str) -> Finding:
    return Finding(
        key=key, rule="R1", severity="minor", finding_type="code_smell", file_path="a.py", line=1
    )


def _confirm(finding: Finding) -> JudgeProposal:
    return JudgeProposal(action="confirm", finding_key=finding.key, rule=finding.rule)


def _disp() -> Disposition:
    return Disposition(action="confirm", routed_to="auto")


def test_chain_links_and_verifies() -> None:
    log = AuditLog()
    for k in ("A", "B", "C"):
        f = _finding(k)
        log.record(f, _confirm(f), _disp(), [])
    entries = log.entries
    assert len(entries) == 3
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[1].prev_hash == entries[0].entry_hash
    assert entries[2].prev_hash == entries[1].entry_hash
    assert log.head == entries[-1].entry_hash
    assert log.verify() is True


def test_tampering_breaks_the_chain() -> None:
    log = AuditLog()
    for k in ("A", "B", "C"):
        f = _finding(k)
        log.record(f, _confirm(f), _disp(), [])
    # Mutate a recorded entry in place; the recomputed hash no longer matches.
    log.entries[1].reason = "silently changed"
    assert log.verify() is False


def test_persists_one_json_line_per_entry(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path=path)
    for k in ("A", "B"):
        f = _finding(k)
        log.record(f, _confirm(f), _disp(), [])
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
