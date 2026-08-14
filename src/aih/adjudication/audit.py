"""Append-only, hash-chained audit log.

Deterministic, pure Python. Each entry's hash covers its content plus the previous entry's
hash, so any edit or deletion in the middle of the log breaks the chain and is detectable
(SPEC decision D5). Records are also mirrored to a JSONL file when a path is given.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aih.adjudication.models import (
    AuditEntry,
    Disposition,
    EvidenceSpan,
    Finding,
    JudgeProposal,
)

GENESIS_HASH = "0" * 64


def _evidence_digest(evidence: list[EvidenceSpan]) -> str:
    """Stable digest of the evidence considered, so the log records *what* was seen."""
    payload = json.dumps(
        [span.model_dump() for span in evidence], sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hash_over(fields: dict[str, object]) -> str:
    material = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _entry_hash(
    finding: Finding,
    proposal: JudgeProposal | None,
    disposition: Disposition,
    evidence_digest: str,
    prev_hash: str,
) -> str:
    return _hash_over(
        {
            "finding_key": finding.key,
            "rule": finding.rule,
            "proposed_action": proposal.action if proposal else "escalate",
            "final_action": disposition.action,
            "routed_to": disposition.routed_to,
            "overridden": disposition.overridden,
            "reason": disposition.reason,
            "evidence_digest": evidence_digest,
            "prev_hash": prev_hash,
        }
    )


class AuditLog:
    """In-memory hash-chained log, optionally persisted to JSONL."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else None
        self._entries: list[AuditEntry] = []
        self._head = GENESIS_HASH

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    @property
    def head(self) -> str:
        return self._head

    def record(
        self,
        finding: Finding,
        proposal: JudgeProposal | None,
        disposition: Disposition,
        evidence: list[EvidenceSpan],
    ) -> AuditEntry:
        """Append one entry for an adjudication and return it."""
        digest = _evidence_digest(evidence)
        entry_hash = _entry_hash(finding, proposal, disposition, digest, self._head)
        entry = AuditEntry(
            finding_key=finding.key,
            rule=finding.rule,
            proposed_action=proposal.action if proposal else "escalate",
            final_action=disposition.action,
            routed_to=disposition.routed_to,
            overridden=disposition.overridden,
            reason=disposition.reason,
            evidence_digest=digest,
            prev_hash=self._head,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        self._head = entry_hash
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(entry.model_dump_json() + "\n")
        return entry

    def verify(self) -> bool:
        """Recompute the chain and confirm no entry was altered or reordered."""
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            recomputed = _hash_over(
                {
                    "finding_key": entry.finding_key,
                    "rule": entry.rule,
                    "proposed_action": entry.proposed_action,
                    "final_action": entry.final_action,
                    "routed_to": entry.routed_to,
                    "overridden": entry.overridden,
                    "reason": entry.reason,
                    "evidence_digest": entry.evidence_digest,
                    "prev_hash": entry.prev_hash,
                }
            )
            if recomputed != entry.entry_hash:
                return False
            prev = entry.entry_hash
        return True
