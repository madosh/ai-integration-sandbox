"""The adjudication state machine.

Each node is a pure ``AdjudicationState -> AdjudicationState`` function — exactly the shape
LangGraph expects — built by a small factory that binds its collaborators. ``run_pipeline``
composes them into a deterministic, dependency-free driver (the default, tested path).
``aih.adjudication.graph`` assembles the *same* node factories into a ``langgraph.StateGraph``
when the optional extra is installed (SPEC decision D1).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from pydantic import BaseModel, Field

from aih.adjudication.audit import AuditLog
from aih.adjudication.evidence import gather_evidence
from aih.adjudication.judge import Judge, RuleBasedJudge
from aih.adjudication.models import (
    AdjudicationResult,
    Disposition,
    EvidenceSpan,
    Finding,
    JudgeProposal,
    Verdict,
)
from aih.adjudication.policy import PolicyConfig, apply_policy
from aih.adjudication.queue import HumanQueue
from aih.adjudication.sources import FixtureSource, SourceProvider


class AdjudicationState(BaseModel):
    """Mutable state threaded through the pipeline nodes."""

    finding: Finding
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    proposal: JudgeProposal | None = None
    disposition: Disposition | None = None
    error: str | None = None


Node = Callable[[AdjudicationState], AdjudicationState]


def gather_evidence_node(source: SourceProvider) -> Node:
    def node(state: AdjudicationState) -> AdjudicationState:
        state.evidence = gather_evidence(state.finding, source)
        return state

    return node


def judge_node(judge: Judge) -> Node:
    def node(state: AdjudicationState) -> AdjudicationState:
        try:
            state.proposal = judge.propose(state.finding, state.evidence)
        except Exception as exc:  # judge is the only fallible node; fail safe.
            state.proposal = None
            state.error = f"judge failed: {exc}"
        return state

    return node


def policy_node(config: PolicyConfig) -> Node:
    def node(state: AdjudicationState) -> AdjudicationState:
        state.disposition = apply_policy(state.finding, state.proposal, config)
        return state

    return node


def finalize_node(audit: AuditLog, queue: HumanQueue) -> Node:
    def node(state: AdjudicationState) -> AdjudicationState:
        disposition = state.disposition
        if disposition is None:  # policy_node always sets one; guard for standalone use.
            return state
        try:
            audit.record(state.finding, state.proposal, disposition, state.evidence)
        except OSError as exc:
            state.error = f"audit write failed: {exc}"
        if disposition.routed_to == "human_queue":
            queue.enqueue(state.finding, state.proposal, disposition, state.evidence)
        return state

    return node


def build_nodes(
    source: SourceProvider,
    judge: Judge,
    config: PolicyConfig,
    audit: AuditLog,
    queue: HumanQueue,
) -> list[Node]:
    """Return the ordered node functions for one adjudication run."""
    return [
        gather_evidence_node(source),
        judge_node(judge),
        policy_node(config),
        finalize_node(audit, queue),
    ]


def _build_verdict(state: AdjudicationState) -> Verdict | None:
    """Record an auto-decided disposition as a safety-checked :class:`Verdict`.

    Escalations are owned by a human, not the schema, so they get no verdict. For a ``dismiss``
    the gate has already guaranteed cited evidence, so this construction cannot raise.
    """
    disposition = state.disposition
    if disposition is None or disposition.action == "escalate":
        return None
    proposal = state.proposal
    cited = (
        [state.evidence[i] for i in proposal.evidence if 0 <= i < len(state.evidence)]
        if proposal
        else []
    )
    return Verdict(
        action=disposition.action,
        finding_key=state.finding.key,
        rule=state.finding.rule,
        evidence=cited,
        rationale=proposal.rationale if proposal else "",
    )


def _run_nodes(state: AdjudicationState, nodes: Sequence[Node]) -> AdjudicationResult:
    for node in nodes:
        state = node(state)
    assert state.disposition is not None  # policy_node guarantees this
    return AdjudicationResult(
        finding=state.finding,
        evidence=state.evidence,
        proposal=state.proposal,
        disposition=state.disposition,
        verdict=_build_verdict(state),
        error=state.error,
    )


def run_pipeline(
    finding: Finding,
    *,
    source: SourceProvider | None = None,
    judge: Judge | None = None,
    policy_config: PolicyConfig | None = None,
    audit: AuditLog | None = None,
    queue: HumanQueue | None = None,
) -> AdjudicationResult:
    """Adjudicate a single finding through the deterministic state machine.

    All collaborators default to their offline implementations, so calling this with just a
    ``Finding`` runs the whole pipeline with no network and no token.
    """
    nodes = build_nodes(
        source or FixtureSource(),
        judge or RuleBasedJudge(),
        policy_config or PolicyConfig(),
        audit or AuditLog(),
        queue or HumanQueue(),
    )
    return _run_nodes(AdjudicationState(finding=finding), nodes)


def run_batch(
    findings: Iterable[Finding],
    *,
    source: SourceProvider | None = None,
    judge: Judge | None = None,
    policy_config: PolicyConfig | None = None,
    audit: AuditLog | None = None,
    queue: HumanQueue | None = None,
) -> list[AdjudicationResult]:
    """Adjudicate many findings sharing one audit log and human queue."""
    source = source or FixtureSource()
    judge = judge or RuleBasedJudge()
    config = policy_config or PolicyConfig()
    audit = audit or AuditLog()
    queue = queue or HumanQueue()
    nodes = build_nodes(source, judge, config, audit, queue)
    return [_run_nodes(AdjudicationState(finding=f), nodes) for f in findings]
