"""Normalized domain models.

Each partner returns differently-shaped payloads; connectors map them onto these
shared models so the rest of the system speaks one language.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CampaignStatus = Literal["active", "paused", "archived", "unknown"]


class Campaign(BaseModel):
    """A normalized advertising campaign record."""

    id: str
    partner: str
    name: str
    status: CampaignStatus = "unknown"
    spend: float = Field(default=0.0, ge=0.0, description="Spend in major currency units.")
    metric: int = Field(default=0, ge=0, description="Primary volume metric (clicks/impressions).")
    raw: dict[str, object] = Field(default_factory=dict, repr=False)


class Creative(BaseModel):
    """A normalized creative asset (image/video/etc.)."""

    id: str
    partner: str
    name: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    checksum: str | None = None


class PushResult(BaseModel):
    """Outcome of a PUSH (publish) operation."""

    id: str
    partner: str
    status: Literal["created", "accepted", "duplicate"] = "created"
    idempotent_hit: bool = False
    detail: str | None = None
