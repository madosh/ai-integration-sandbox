"""Skill: sync_campaign_data (read-only).

Pull campaign records from one connector, normalize, compute totals, and summarize
via the LLMClient.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from aih.llm.base import ChatMessage
from aih.skills.base import Skill, SkillContext


class SyncCampaignInput(BaseModel):
    connector: str = Field(description="Connector name, e.g. 'novareach' or 'pulseads'.")
    resource: str = "campaigns"
    limit: int = Field(default=50, ge=1, le=1000)


class SyncCampaignOutput(BaseModel):
    connector: str
    count: int
    total_spend: float
    summary: str
    records: list[dict[str, Any]]


class SyncCampaignData(Skill):
    name = "sync_campaign_data"
    description = "Pull and summarize campaign records from a connector (read-only)."
    side_effect = False
    input_model: ClassVar[type[BaseModel]] = SyncCampaignInput
    output_model: ClassVar[type[BaseModel]] = SyncCampaignOutput

    async def run(self, payload: BaseModel, ctx: SkillContext) -> SyncCampaignOutput:
        assert isinstance(payload, SyncCampaignInput)
        connector = ctx.get_connector(payload.connector)
        try:
            records: list[dict[str, Any]] = []
            total_spend = 0.0
            async for campaign in connector.get_records(payload.resource):
                records.append(campaign.model_dump(exclude={"raw"}))
                total_spend += campaign.spend
                if len(records) >= payload.limit:
                    break
        finally:
            await connector.aclose()

        prompt = (
            f"Summarize {len(records)} campaigns from {payload.connector} "
            f"with total spend {total_spend:.2f}."
        )
        completion = await ctx.llm.complete([ChatMessage(role="user", content=prompt)])
        return SyncCampaignOutput(
            connector=payload.connector,
            count=len(records),
            total_spend=round(total_spend, 2),
            summary=completion.text,
            records=records,
        )
