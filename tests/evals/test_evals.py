"""Tests for the eval harness."""

from __future__ import annotations

import json
from pathlib import Path

from aih.evals.review_queue import export_review_queue, ingest_human_scores, load_jsonl
from aih.evals.runner import run_evals
from aih.evals.scorers import (
    exact_match,
    mrr_for_ranks,
    ndcg_at_k,
    recall_at_k,
    rubric_keyword_score,
    structured_match,
    tool_selection_accuracy,
)
from aih.evals.suites import run_generation_suite, run_retrieval_suite, run_tool_selection_suite


def test_exact_match() -> None:
    assert exact_match("Hello", "hello") == 1.0
    assert exact_match("a", "b") == 0.0


def test_structured_match() -> None:
    score = structured_match({"a": "x", "b": "y"}, {"a": "x", "b": "z"}, ["a", "b"])
    assert score == 0.5


def test_retrieval_scorers() -> None:
    relevant = {"d1", "d2"}
    retrieved = ["d2", "d3", "d1"]
    assert recall_at_k(relevant, retrieved, 2) == 0.5
    assert mrr_for_ranks([1, 2]) == 0.75
    assert ndcg_at_k(relevant, retrieved, 3) > 0.0


def test_tool_selection_accuracy() -> None:
    assert tool_selection_accuracy("publish_creative", "publish_creative") == 1.0
    assert tool_selection_accuracy("a", "b") == 0.0


def test_rubric_keyword_score() -> None:
    score = rubric_keyword_score("retry after backoff jitter", "retry backoff rate limit")
    assert score >= 0.5


async def test_retrieval_suite() -> None:
    result = await run_retrieval_suite()
    assert result.samples >= 3
    assert any(m.name == "retrieval.mrr" for m in result.metrics)


async def test_generation_suite() -> None:
    suite, rows = await run_generation_suite()
    assert suite.samples >= 2
    assert rows and rows[0]["human_score"] is None


async def test_tool_selection_suite() -> None:
    result = await run_tool_selection_suite()
    assert result.metrics[0].value >= 0.66


async def test_full_eval_run_produces_scorecard() -> None:
    scorecard = await run_evals()
    assert len(scorecard.suites) == 5
    assert scorecard.report_path is not None


def test_review_queue_roundtrip(tmp_path: Path) -> None:
    rows = [
        {
            "id": "x1",
            "suite": "generation",
            "input": {"q": "test"},
            "prediction": "answer",
            "auto_score": 0.5,
            "human_score": None,
            "rubric": "test rubric",
        }
    ]
    json_path, _ = export_review_queue(rows, out_dir=tmp_path)
    reviewed = json.loads(json_path.read_text(encoding="utf-8"))
    reviewed[0]["human_score"] = 0.9
    reviewed_path = tmp_path / "reviewed.json"
    reviewed_path.write_text(json.dumps(reviewed), encoding="utf-8")
    scores = ingest_human_scores(reviewed_path)
    assert scores["x1"] == 0.9


def test_load_jsonl() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "aih"
        / "evals"
        / "datasets"
        / "retrieval.jsonl"
    )
    records = load_jsonl(path)
    assert len(records) >= 3
