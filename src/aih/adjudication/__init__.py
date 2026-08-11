"""AI adjudication layer over static-analysis findings.

An LLM proposes a verdict (confirm / dismiss / escalate) over gathered code evidence; a
deterministic policy gate then routes anything consequential to a human queue and never
auto-closes a real security finding. Offline-by-default: the shipped source and judge are fakes,
so the whole pipeline runs with no token and no network. See ``SPEC.md``.
"""

from aih.adjudication.audit import AuditLog
from aih.adjudication.evidence import gather_evidence
from aih.adjudication.judge import Judge, RuleBasedJudge
from aih.adjudication.models import (
    AdjudicationResult,
    AuditEntry,
    Disposition,
    EvidenceSpan,
    Finding,
    JudgeProposal,
    Verdict,
)
from aih.adjudication.pipeline import AdjudicationState, run_batch, run_pipeline
from aih.adjudication.policy import PolicyConfig, apply_policy, is_consequential
from aih.adjudication.queue import HumanQueue, QueueItem
from aih.adjudication.sources import (
    FixtureSource,
    InMemorySource,
    SonarQubeMCPSource,
    SourceProvider,
)

__all__ = [
    "AdjudicationResult",
    "AdjudicationState",
    "AuditEntry",
    "AuditLog",
    "Disposition",
    "EvidenceSpan",
    "Finding",
    "FixtureSource",
    "HumanQueue",
    "InMemorySource",
    "Judge",
    "JudgeProposal",
    "PolicyConfig",
    "QueueItem",
    "RuleBasedJudge",
    "SonarQubeMCPSource",
    "SourceProvider",
    "Verdict",
    "apply_policy",
    "gather_evidence",
    "is_consequential",
    "run_batch",
    "run_pipeline",
]
