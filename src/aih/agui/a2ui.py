"""A2UI declarative component specs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApprovalCardSpec(BaseModel):
    component: Literal["ApprovalCard"] = "ApprovalCard"
    action: str
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    reversibility: Literal["low", "medium", "high"] = "low"
    approve_label: str = "Approve"
    deny_label: str = "Deny"
    description: str = ""


class MetricCardSpec(BaseModel):
    component: Literal["MetricCard"] = "MetricCard"
    title: str
    metrics: dict[str, Any] = Field(default_factory=dict)


def approval_card_from_step(
    action: str, preview: dict[str, Any], *, description: str = ""
) -> dict[str, Any]:
    return ApprovalCardSpec(
        action=action,
        payload_preview=preview,
        description=description or f"Approve side-effecting action: {action}",
    ).model_dump()


def metric_card(title: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return MetricCardSpec(title=title, metrics=metrics).model_dump()
