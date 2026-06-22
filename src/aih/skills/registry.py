"""Skill registry — discoverable, mirroring the connector registry."""

from __future__ import annotations

from typing import Any

from aih.llm.base import ToolSpec
from aih.skills.answer_from_docs import AnswerFromDocs
from aih.skills.base import Skill
from aih.skills.publish_creative import PublishCreative
from aih.skills.sync_all_connectors import SyncAllConnectors
from aih.skills.sync_campaign_data import SyncCampaignData


class SkillRegistry:
    """Registry of skill instances keyed by name."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def names(self) -> list[str]:
        return sorted(self._skills)

    def has(self, name: str) -> bool:
        return name in self._skills

    def get(self, name: str) -> Skill:
        if name not in self._skills:
            raise KeyError(f"unknown skill: {name!r}; known: {self.names()}")
        return self._skills[name]

    def describe(self) -> list[dict[str, Any]]:
        return [type(self._skills[n]).describe() for n in self.names()]

    def tool_specs(self) -> list[ToolSpec]:
        return [type(self._skills[n]).tool_spec() for n in self.names()]


def default_registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(SyncCampaignData())
    reg.register(SyncAllConnectors())
    reg.register(PublishCreative())
    reg.register(AnswerFromDocs())
    return reg


#: Process-wide default skill registry.
SKILLS = default_registry()
