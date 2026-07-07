"""Schema mapping layer — raw partner payloads → canonical models with drift notes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    """Maps a partner field path to a canonical field."""

    source: str
    target: str
    transform: str | None = None  # e.g. "cents_to_dollars"


class PartnerMapping(BaseModel):
    """Mapping spec for one partner resource."""

    partner: str
    resource: str
    version: str = "1"
    fields: list[FieldMapping] = Field(default_factory=list)


# Registry of known mappings (handles partner schema drift)
MAPPINGS: dict[str, PartnerMapping] = {
    "pulseads:campaigns": PartnerMapping(
        partner="pulseads",
        resource="campaigns",
        version="1",
        fields=[
            FieldMapping(source="spend_cents", target="spend", transform="cents_to_dollars"),
            FieldMapping(source="campaign_id", target="id"),
        ],
    ),
    "novareach:campaigns": PartnerMapping(
        partner="novareach",
        resource="campaigns",
        version="1",
        fields=[
            FieldMapping(source="budget", target="spend"),
            FieldMapping(source="id", target="id"),
        ],
    ),
}


def apply_transform(value: Any, transform: str | None) -> Any:
    if transform == "cents_to_dollars" and isinstance(value, (int, float)):
        return float(value) / 100.0
    return value


def map_raw(partner: str, resource: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Apply registered field mappings to a raw partner record."""
    key = f"{partner}:{resource}"
    spec = MAPPINGS.get(key)
    if spec is None:
        return dict(raw)
    out: dict[str, Any] = {}
    for fm in spec.fields:
        if fm.source in raw:
            out[fm.target] = apply_transform(raw[fm.source], fm.transform)
    for k, v in raw.items():
        if k not in {fm.source for fm in spec.fields}:
            out.setdefault(k, v)
    return out
