"""Skill: publish_creative (side-effecting).

Push a creative to a connector. This skill is side-effecting; the agent MUST route
it through the approval gate before calling ``run``.
"""

from __future__ import annotations

import base64
from typing import ClassVar

from pydantic import BaseModel, Field

from aih.skills.base import Skill, SkillContext


class PublishCreativeInput(BaseModel):
    connector: str = Field(description="Connector to publish to, e.g. 'creativebox'.")
    name: str = Field(default="creative.png", description="Creative file name.")
    content_b64: str = Field(
        default="",
        description="Base64-encoded creative bytes. If not valid base64, treated as raw text.",
    )
    content_type: str = "image/png"


class PublishCreativeOutput(BaseModel):
    id: str
    partner: str
    status: str
    idempotent_hit: bool


def _decode(content_b64: str) -> bytes:
    """Decode base64; fall back to UTF-8 bytes so fabricated args still work."""
    if not content_b64:
        return b"\x89PNG\r\n placeholder creative bytes"
    try:
        # binascii.Error (raised on bad padding/chars) is a subclass of ValueError.
        return base64.b64decode(content_b64, validate=True)
    except ValueError:
        return content_b64.encode("utf-8")


class PublishCreative(Skill):
    name = "publish_creative"
    description = "Publish (upload) a creative asset to a connector. Side-effecting."
    side_effect = True
    input_model: ClassVar[type[BaseModel]] = PublishCreativeInput
    output_model: ClassVar[type[BaseModel]] = PublishCreativeOutput

    async def run(self, payload: BaseModel, ctx: SkillContext) -> PublishCreativeOutput:
        assert isinstance(payload, PublishCreativeInput)
        connector = ctx.get_connector(payload.connector)
        try:
            result = await connector.push_creative(
                name=payload.name,
                content=_decode(payload.content_b64),
                content_type=payload.content_type,
            )
        finally:
            await connector.aclose()
        return PublishCreativeOutput(
            id=result.id,
            partner=result.partner,
            status=result.status,
            idempotent_hit=result.idempotent_hit,
        )
