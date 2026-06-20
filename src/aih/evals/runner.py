"""Eval harness entrypoint: ``python -m aih.evals.runner`` or ``python tasks.py eval``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aih.evals.models import Scorecard
from aih.evals.review_queue import export_review_queue, ingest_human_scores
from aih.evals.suites import (
    run_generation_suite,
    run_redteam_suite,
    run_rerank_suite,
    run_retrieval_suite,
    run_tool_selection_suite,
)

ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "evals" / "reports"
THRESHOLDS_PATH = Path(__file__).parent / "thresholds.json"


def _load_thresholds() -> dict[str, float]:
    raw = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in raw.items()}


def _apply_thresholds(scorecard: Scorecard, thresholds: dict[str, float]) -> None:
    for suite in scorecard.suites:
        for metric in suite.metrics:
            thr = thresholds.get(metric.name)
            if thr is not None:
                metric.threshold = thr
                metric.passed = metric.value >= thr


def _print_scorecard(scorecard: Scorecard) -> None:
    print("\n=== EVAL SCORECARD ===")
    for suite in scorecard.suites:
        print(f"\n[{suite.suite}] ({suite.samples} samples)")
        for m in suite.metrics:
            status = "PASS" if m.passed else "FAIL"
            thr = f" (threshold {m.threshold})" if m.threshold is not None else ""
            print(f"  {m.name}: {m.value:.3f}{thr} [{status}]")
    failed = scorecard.failed()
    if failed:
        print("\nFAILED METRICS:")
        for m in failed:
            print(f"  - {m.name}: {m.value:.3f} < {m.threshold}")
    else:
        print("\nAll metrics passed.")


async def run_evals() -> Scorecard:
    thresholds = _load_thresholds()
    retrieval = await run_retrieval_suite()
    generation, review_rows = await run_generation_suite()
    tool_sel = await run_tool_selection_suite()
    redteam = await run_redteam_suite()
    rerank = await run_rerank_suite()

    scorecard = Scorecard(
        suites=[retrieval, generation, tool_sel, redteam, rerank],
        timestamp=datetime.now(UTC).isoformat(),
    )
    _apply_thresholds(scorecard, thresholds)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"scorecard_{stamp}.json"
    report_path.write_text(scorecard.model_dump_json(indent=2), encoding="utf-8")
    scorecard.report_path = str(report_path)

    review_json, review_csv = export_review_queue(
        review_rows, out_dir=REPORTS_DIR, prefix=f"review_{stamp}"
    )
    print(f"Review queue: {review_json} , {review_csv}")

    # Demonstrate re-ingest: fold a synthetic human score for the first row.
    if review_rows:
        reviewed_path = REPORTS_DIR / f"review_{stamp}_reviewed.json"
        reviewed = json.loads(review_json.read_text(encoding="utf-8"))
        reviewed[0]["human_score"] = 1.0
        reviewed_path.write_text(json.dumps(reviewed, indent=2), encoding="utf-8")
        human = ingest_human_scores(reviewed_path)
        print(f"Re-ingested human scores for ids: {list(human.keys())}")

    _print_scorecard(scorecard)
    return scorecard


def main() -> int:
    import asyncio

    scorecard = asyncio.run(run_evals())
    return 1 if scorecard.failed() else 0


if __name__ == "__main__":
    raise SystemExit(main())
