"""The regression gate: false-dismissal rate must be zero on the golden labelled set."""

from __future__ import annotations

import json
from pathlib import Path

from aih.evals.suites import run_adjudication_suite

# Read at import time (sync) so the async tests never touch the filesystem.
_THRESHOLDS = json.loads(Path("src/aih/evals/thresholds.json").read_text(encoding="utf-8"))


async def test_false_dismissal_rate_is_zero() -> None:
    result = await run_adjudication_suite()
    metric = result.metrics[0]
    assert metric.name == "adjudication.no_false_dismissal"
    assert metric.value == 1.0

    detail = result.details[0]
    assert detail["false_dismissal_rate"] == 0.0
    assert detail["false_dismissals"] == []
    assert detail["keep_findings"] > 0  # the set actually exercises KEEP findings


async def test_metric_passes_configured_threshold() -> None:
    result = await run_adjudication_suite()
    threshold = _THRESHOLDS["adjudication.no_false_dismissal"]
    assert result.metrics[0].value >= threshold


async def test_dataset_covers_both_labels_and_all_actions() -> None:
    result = await run_adjudication_suite()
    actions = set(result.details[0]["dispositions"].values())
    # The golden set exercises the full disposition space, not just the safe default.
    assert {"confirm", "dismiss", "escalate"} <= actions
