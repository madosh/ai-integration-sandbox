"""Skill base class + execution context.

A Skill is a reusable, well-scoped capability with typed I/O. The agent discovers
skills via the registry and invokes them; side-effecting skills are gated by the
human-in-the-loop approver before ``run`` is called.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel

from aih.connectors.base import Connector
from aih.connectors.registry import REGISTRY, ConnectorRegistry, default_config
from aih.llm import get_embedder, get_llm
from aih.llm.base import Embedder, LLMClient, ToolSpec
from aih.rag.retriever import HybridRetriever


@dataclass
class SkillContext:
    """Dependencies a skill needs at run time.

    ``httpx_transport`` lets skills run fully offline in tests (connectors mount the
    mock APIs in-process). ``retriever`` is lazily created if not provided.
    """

    llm: LLMClient
    registry: ConnectorRegistry = REGISTRY
    retriever: HybridRetriever | None = None
    embedder: Embedder | None = None
    httpx_transport: httpx.AsyncBaseTransport | None = None

    @classmethod
    def default(cls) -> SkillContext:
        return cls(llm=get_llm(), embedder=get_embedder())

    def get_connector(self, name: str) -> Connector:
        return self.registry.build(name, default_config(name, httpx_transport=self.httpx_transport))

    def get_retriever(self) -> HybridRetriever:
        if self.retriever is None:
            self.retriever = HybridRetriever(embedder=self.embedder)
        return self.retriever


class Skill(ABC):
    """Base class for reusable AI Skills."""

    name: ClassVar[str]
    description: ClassVar[str]
    side_effect: ClassVar[bool] = False
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, payload: BaseModel, ctx: SkillContext) -> BaseModel:
        """Execute the skill against a validated input payload."""

    @classmethod
    def tool_spec(cls) -> ToolSpec:
        """Expose the skill as a function-calling tool spec for the planner."""
        return ToolSpec(
            name=cls.name,
            description=cls.description,
            parameters=cls.input_model.model_json_schema(),
        )

    @classmethod
    def describe(cls) -> dict[str, Any]:
        return {
            "name": cls.name,
            "description": cls.description,
            "side_effect": cls.side_effect,
            "input_schema": cls.input_model.model_json_schema(),
        }
