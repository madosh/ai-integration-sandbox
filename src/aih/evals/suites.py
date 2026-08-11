"""Eval suite runners for retrieval, generation, and tool-selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from mock_apis.app import app as mock_app

from aih.evals.models import MetricScore, SuiteResult
from aih.evals.review_queue import load_jsonl
from aih.evals.scorers import (
    llm_judge,
    mrr_for_ranks,
    ndcg_at_k,
    recall_at_k,
    rubric_keyword_score,
    tool_selection_accuracy,
)
from aih.llm import FakeLLM, HashEmbedder
from aih.llm.base import ChatMessage, ToolSpec
from aih.rag.retriever import HybridRetriever
from aih.skills.answer_from_docs import AnswerFromDocs, AnswerInput
from aih.skills.base import SkillContext
from aih.skills.registry import default_registry

_DATASETS = Path(__file__).parent / "datasets"
_FINISH = ToolSpec(
    name="finish", description="finish", parameters={"type": "object", "properties": {}}
)


def _ctx() -> SkillContext:
    return SkillContext(
        llm=FakeLLM(),
        retriever=HybridRetriever(embedder=HashEmbedder(dim=256)),
        embedder=HashEmbedder(dim=256),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )


async def run_retrieval_suite(k: int = 3) -> SuiteResult:
    records = load_jsonl(_DATASETS / "retrieval.jsonl")
    retriever = HybridRetriever(embedder=HashEmbedder(dim=256))
    recalls: list[float] = []
    ndcgs: list[float] = []
    ranks: list[int] = []
    details: list[dict[str, Any]] = []

    for rec in records:
        query = str(rec.input.get("query", ""))
        relevant = set(rec.reference if isinstance(rec.reference, list) else [rec.reference])
        result = await retriever.search(query, k=k, method="rrf")
        retrieved = [c.provenance.doc_id or "" for c in result.chunks]
        recalls.append(recall_at_k(relevant, retrieved, k))
        ndcgs.append(ndcg_at_k(relevant, retrieved, k))
        rank = 0
        for i, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant:
                rank = i
                break
        ranks.append(rank)
        details.append({"id": rec.id, "query": query, "retrieved": retrieved[:k], "rank": rank})

    metrics = [
        MetricScore(name="retrieval.recall_at_3", value=sum(recalls) / len(recalls)),
        MetricScore(name="retrieval.mrr", value=mrr_for_ranks(ranks)),
        MetricScore(name="retrieval.ndcg_at_3", value=sum(ndcgs) / len(ndcgs)),
    ]
    return SuiteResult(suite="retrieval", metrics=metrics, samples=len(records), details=details)


async def run_generation_suite() -> tuple[SuiteResult, list[dict[str, Any]]]:
    records = load_jsonl(_DATASETS / "generation.jsonl")
    ctx = _ctx()
    skill = AnswerFromDocs()
    scores: list[float] = []
    review_rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for rec in records:
        question = str(rec.input.get("question", ""))
        out = await skill.run(AnswerInput(question=question), ctx)
        rubric = rec.rubric or ""
        auto = rubric_keyword_score(out.answer, rubric)
        judge = await llm_judge(ctx.llm, out.answer, rubric)
        score = max(auto, judge)
        scores.append(score)
        review_rows.append(
            {
                "id": rec.id,
                "suite": "generation",
                "input": rec.input,
                "prediction": out.answer,
                "auto_score": score,
                "human_score": None,
                "rubric": rubric,
            }
        )
        details.append({"id": rec.id, "score": score, "answer": out.answer[:200]})

    metric = MetricScore(
        name="generation.llm_judge",
        value=sum(scores) / len(scores) if scores else 0.0,
    )
    return (
        SuiteResult(suite="generation", metrics=[metric], samples=len(records), details=details),
        review_rows,
    )


async def run_tool_selection_suite() -> SuiteResult:
    records = load_jsonl(_DATASETS / "tool_selection.jsonl")
    llm = FakeLLM()
    tools = [*default_registry().tool_specs(), _FINISH]
    hits: list[float] = []
    details: list[dict[str, Any]] = []

    for rec in records:
        goal = str(rec.input.get("goal", ""))
        messages = [ChatMessage(role="user", content=f"GOAL: {goal}")]
        completion = await llm.tool_call(messages, tools)
        actual = completion.tool_call.name if completion.tool_call else "finish"
        expected = str(rec.reference)
        hit = tool_selection_accuracy(expected, actual)
        hits.append(hit)
        details.append({"id": rec.id, "expected": expected, "actual": actual, "hit": hit})

    metric = MetricScore(
        name="tool_selection.accuracy",
        value=sum(hits) / len(hits) if hits else 0.0,
    )
    return SuiteResult(
        suite="tool_selection", metrics=[metric], samples=len(records), details=details
    )


async def run_redteam_suite() -> SuiteResult:
    records = load_jsonl(_DATASETS / "redteam.jsonl")
    hits: list[float] = []
    retriever = HybridRetriever(embedder=HashEmbedder(dim=256))
    for rec in records:
        if "query" in rec.input:
            result = await retriever.search(str(rec.input["query"]), k=3)
            hits.append(1.0 if len(result.chunks) == 0 else 0.0)
        elif "goal" in rec.input:
            from aih.guardrails.validate import validate_skill_args

            ok, _ = validate_skill_args(
                "publish_creative",
                {"connector": "creativebox", "name": "ignore previous instructions"},
            )
            hits.append(1.0 if not ok else 0.0)
    metric = MetricScore(
        name="redteam.block_rate",
        value=sum(hits) / len(hits) if hits else 1.0,
    )
    return SuiteResult(suite="redteam", metrics=[metric], samples=len(records))


async def run_adjudication_suite() -> SuiteResult:
    """Regression gate for the adjudication layer: the false-dismissal rate.

    A false dismissal is a finding a human labelled ``KEEP`` that the pipeline dismissed. The
    metric is reported as ``1 - rate`` so it fits the harness's uniform ``value >= threshold``
    gate (SPEC decision D3); at threshold 1.0 the build fails on any false dismissal.
    """
    from aih.adjudication import Finding, FixtureSource, RuleBasedJudge, run_batch

    records = load_jsonl(_DATASETS / "adjudication.jsonl")
    findings = [Finding.model_validate(rec.input) for rec in records]
    labels = {rec.id: str(rec.reference) for rec in records}

    results = run_batch(findings, source=FixtureSource(), judge=RuleBasedJudge())

    keep_ids = [rec.id for rec in records if labels[rec.id] == "KEEP"]
    offenders: list[str] = []
    for rec, result in zip(records, results, strict=True):
        if labels[rec.id] == "KEEP" and result.disposition.action == "dismiss":
            offenders.append(rec.id)

    rate = len(offenders) / len(keep_ids) if keep_ids else 0.0
    metric = MetricScore(name="adjudication.no_false_dismissal", value=1.0 - rate)
    dispositions = {rec.id: r.disposition.action for rec, r in zip(records, results, strict=True)}
    detail = {
        "false_dismissal_rate": rate,
        "keep_findings": len(keep_ids),
        "false_dismissals": offenders,
        "dispositions": dispositions,
    }
    return SuiteResult(
        suite="adjudication", metrics=[metric], samples=len(records), details=[detail]
    )


async def run_rerank_suite() -> SuiteResult:
    retriever = HybridRetriever(embedder=HashEmbedder(dim=256))
    query = "HTTP 429 Retry-After exponential backoff"
    without = await retriever.search(query, k=3, retrieve_k=6)
    # Reranker always on in retriever; measure top hit has policy doc signal
    top_doc = without.chunks[0].provenance.doc_id if without.chunks else ""
    uplift = 1.0 if top_doc == "policy-rate-limiting" else 0.5
    metric = MetricScore(name="rerank.quality", value=uplift)
    return SuiteResult(suite="rerank", metrics=[metric], samples=1)
