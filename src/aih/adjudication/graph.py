"""Optional LangGraph wiring for the adjudication state machine (SPEC decision D1).

The default, tested pipeline is the dependency-free driver in :mod:`aih.adjudication.pipeline`.
This module assembles the **same** node factories into a ``langgraph.StateGraph`` for anyone who
wants the LangGraph runtime in production. ``langgraph`` is imported lazily inside
:func:`build_langgraph`, behind the optional ``graph`` extra, so it is never required on the
offline test path.

    from aih.adjudication.graph import build_langgraph
    app = build_langgraph(source, judge, config, audit, queue)
    final_state = app.invoke({"finding": finding})
"""

from __future__ import annotations

from typing import Any

from aih.adjudication.audit import AuditLog
from aih.adjudication.judge import Judge
from aih.adjudication.pipeline import (
    AdjudicationState,
    finalize_node,
    gather_evidence_node,
    judge_node,
    policy_node,
)
from aih.adjudication.policy import PolicyConfig
from aih.adjudication.queue import HumanQueue
from aih.adjudication.sources import SourceProvider


def build_langgraph(
    source: SourceProvider,
    judge: Judge,
    config: PolicyConfig,
    audit: AuditLog,
    queue: HumanQueue,
) -> Any:
    """Build and compile a LangGraph ``StateGraph`` over the adjudication nodes.

    Requires ``pip install 'aih[graph]'``. Node bodies are identical to the offline driver — the
    only thing LangGraph changes is who calls them.
    """
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "LangGraph is optional; install with `pip install 'aih[graph]'` to use build_langgraph"
        ) from exc

    gather = gather_evidence_node(source)
    judge_fn = judge_node(judge)
    gate = policy_node(config)
    finalize = finalize_node(audit, queue)

    graph: Any = StateGraph(AdjudicationState)
    graph.add_node("gather_evidence", gather)
    graph.add_node("judge", judge_fn)
    graph.add_node("policy_gate", gate)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "gather_evidence")
    graph.add_edge("gather_evidence", "judge")
    graph.add_edge("judge", "policy_gate")
    graph.add_edge("policy_gate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
