"""Human-in-the-loop review queue export and re-ingest."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from aih.evals.models import EvalRecord


def export_review_queue(
    records: list[dict[str, Any]],
    *,
    out_dir: Path,
    prefix: str = "review",
) -> tuple[Path, Path]:
    """Write a review queue as JSON and CSV with blank ``human_score`` fields."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{prefix}.json"
    csv_path = out_dir / f"{prefix}.csv"

    queue = [
        {
            "id": r.get("id", ""),
            "suite": r.get("suite", ""),
            "input": r.get("input", {}),
            "prediction": r.get("prediction", ""),
            "auto_score": r.get("auto_score"),
            "human_score": r.get("human_score"),
            "rubric": r.get("rubric"),
        }
        for r in records
    ]

    json_path.write_text(json.dumps(queue, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "suite",
                "input",
                "prediction",
                "auto_score",
                "human_score",
                "rubric",
            ],
        )
        writer.writeheader()
        for row in queue:
            writer.writerow(
                {
                    "id": row["id"],
                    "suite": row["suite"],
                    "input": json.dumps(row["input"]),
                    "prediction": row["prediction"],
                    "auto_score": row["auto_score"],
                    "human_score": row["human_score"] or "",
                    "rubric": row["rubric"] or "",
                }
            )

    return json_path, csv_path


def ingest_human_scores(path: Path) -> dict[str, float]:
    """Read human scores from a reviewed JSON or CSV file."""
    if path.suffix.lower() == ".csv":
        scores: dict[str, float] = {}
        with path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                raw = (row.get("human_score") or "").strip()
                if raw:
                    scores[row["id"]] = float(raw)
        return scores

    data = json.loads(path.read_text(encoding="utf-8"))
    scores = {}
    for row in data:
        hs = row.get("human_score")
        if hs is not None and str(hs).strip() != "":
            scores[row["id"]] = float(hs)
    return scores


def load_jsonl(path: Path) -> list[EvalRecord]:
    """Load a JSONL dataset."""
    records: list[EvalRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(EvalRecord.model_validate_json(line))
    return records
