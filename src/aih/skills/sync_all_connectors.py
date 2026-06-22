"""Skill: sync_all_connectors — parallel read-only sync across all partners."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from aih.connectors.registry import REGISTRY
from aih.skills.base import Skill, SkillContext
from aih.skills.sync_campaign_data import SyncCampaignData, SyncCampaignInput


class SyncAllInput(BaseModel):
    resource: str = "campaigns"
    limit_per_connector: int = Field(default=20, ge=1, le=500)


class SyncAllOutput(BaseModel):
    total_records: int
    connectors: list[dict[str, Any]]
    errors: list[dict[str, str]]


class SyncAllConnectors(Skill):
    name = "sync_all_connectors"
    description = "Pull campaign records from every registered connector in parallel (read-only)."
    side_effect = False
    input_model: ClassVar[type[BaseModel]] = SyncAllInput
    output_model: ClassVar[type[BaseModel]] = SyncAllOutput

    async def run(self, payload: BaseModel, ctx: SkillContext) -> SyncAllOutput:
        assert isinstance(payload, SyncAllInput)
        sync = SyncCampaignData()
        names = REGISTRY.names()

        async def _one(name: str) -> tuple[str, dict[str, Any] | None, str | None]:
            try:
                out = await sync.run(
                    SyncCampaignInput(
                        connector=name,
                        resource=payload.resource,
                        limit=payload.limit_per_connector,
                    ),
                    ctx,
                )
                return name, out.model_dump(), None
            except Exception as exc:  # noqa: BLE001
                return name, None, str(exc)

        results = await asyncio.gather(*[_one(n) for n in names])
        connectors: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        total = 0
        for name, data, err in results:
            if err:
                errors.append({"connector": name, "error": err})
            elif data:
                connectors.append(data)
                total += int(data.get("count", 0))
        return SyncAllOutput(total_records=total, connectors=connectors, errors=errors)
