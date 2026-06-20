"""Online eval sampling from production-style run traces."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from aih.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
ONLINE_DIR = ROOT / "evals" / "reports" / "online"


def maybe_sample_run(trace_summary: dict[str, Any]) -> Path | None:
    """Sample a fraction of runs into the online review queue."""
    rate = get_settings().online_eval_sample_rate
    if rate <= 0 or random.random() > rate:
        return None
    ONLINE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = trace_summary.get("run_id", "unknown")
    path = ONLINE_DIR / f"sample_{run_id}.json"
    path.write_text(json.dumps(trace_summary, indent=2), encoding="utf-8")
    return path
