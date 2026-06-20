"""Pydantic models for the eval harness."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalRecord(BaseModel):
    """One row from a golden dataset (JSONL)."""

    id: str
    input: dict[str, Any] = Field(default_factory=dict)
    reference: Any = None
    rubric: str | None = None


class MetricScore(BaseModel):
    """A single metric name and its value."""

    name: str
    value: float
    threshold: float | None = None
    passed: bool = True


class SuiteResult(BaseModel):
    """Results for one eval suite."""

    suite: str
    metrics: list[MetricScore] = Field(default_factory=list)
    samples: int = 0
    details: list[dict[str, Any]] = Field(default_factory=list)


class Scorecard(BaseModel):
    """Aggregated scorecard across all suites."""

    suites: list[SuiteResult] = Field(default_factory=list)
    timestamp: str = ""
    report_path: str | None = None

    def all_metrics(self) -> list[MetricScore]:
        out: list[MetricScore] = []
        for suite in self.suites:
            out.extend(suite.metrics)
        return out

    def failed(self) -> list[MetricScore]:
        return [m for m in self.all_metrics() if not m.passed]
