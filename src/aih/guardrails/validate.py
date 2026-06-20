"""Structured output validation before side effects."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError


def validate_structured(model: type[BaseModel], data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate dict against a Pydantic model; return (ok, error_message)."""
    try:
        model.model_validate(data)
        return True, None
    except ValidationError as exc:
        return False, str(exc.errors()[0]["msg"])


def validate_skill_args(skill_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
    """Guardrail: block empty connector names and injection in string fields."""
    if skill_name in {"sync_campaign_data", "publish_creative"}:
        conn = str(args.get("connector", "")).strip()
        if not conn:
            return False, "connector is required"
        if len(conn) > 64:
            return False, "connector name too long"
    for key, val in args.items():
        if isinstance(val, str) and "ignore previous" in val.lower():
            return False, f"injection pattern in field {key}"
    return True, None
