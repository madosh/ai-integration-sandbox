"""Shared fixtures: connectors wired to the in-process mock app (offline)."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.connectors.base import Connector
from aih.connectors.registry import REGISTRY, default_config


class SleepRecorder:
    """A fast, async sleep that records the delays it was asked to wait."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.fixture(autouse=True)
def _reset_mock_state() -> Iterator[None]:
    reset_state()
    yield
    reset_state()


@pytest.fixture
def sleeper() -> SleepRecorder:
    return SleepRecorder()


@pytest.fixture
def make_connector(sleeper: SleepRecorder):  # type: ignore[no-untyped-def]
    """Factory building a connector wired to the mock app with a fast sleep."""
    transport = httpx.ASGITransport(app=mock_app)

    def _build(name: str) -> Connector:
        config = default_config(name, httpx_transport=transport, sleep=sleeper)
        return REGISTRY.build(name, config)

    return _build
