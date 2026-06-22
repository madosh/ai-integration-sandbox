"""Build Agent Card from the skills registry."""

from __future__ import annotations

from aih.a2a.models import AgentCard, AgentSkill
from aih.skills.registry import SKILLS


def build_agent_card(*, base_url: str = "http://127.0.0.1:8000") -> AgentCard:
    skills = [
        AgentSkill(
            id=s["name"],
            name=s["name"],
            description=s.get("description", ""),
            tags=["integration", "offline"],
        )
        for s in SKILLS.describe()
        if s["name"] in {"sync_campaign_data", "publish_creative", "answer_from_docs"}
    ]
    return AgentCard(
        name="ai-integration-hub",
        description="Offline-first integration agent with connectors, hybrid RAG, and HITL.",
        url=f"{base_url}/a2a",
        skills=skills,
    )
