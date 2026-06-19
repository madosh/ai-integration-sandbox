"""Retry-on-429 (honoring Retry-After), auth failures, and the circuit breaker."""

from __future__ import annotations

import httpx
import pytest
from mock_apis.app import app as mock_app

from aih.connectors.auth import BearerAuth
from aih.connectors.base import ConnectorConfig
from aih.connectors.errors import AuthError, CircuitOpenError
from aih.connectors.pulseads import PulseAdsConnector
from aih.connectors.transport import CircuitBreaker, RetryPolicy


async def test_forced_429_then_success(make_connector, sleeper) -> None:  # type: ignore[no-untyped-def]
    # Arm one 429 on PulseAds, then read: the transport should retry and succeed.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mock_app), base_url="http://test"
    ) as client:
        await client.post("/pulseads/_arm_rate_limit", params={"count": 1})

    connector = make_connector("pulseads")
    records = [c async for c in connector.get_records()]
    await connector.aclose()

    assert len(records) == 5
    # The retry honored Retry-After: 1 (recorded by the fast sleeper).
    assert 1.0 in sleeper.delays


async def test_auth_failure_raises_typed_error(sleeper) -> None:  # type: ignore[no-untyped-def]
    bad = ConnectorConfig(
        base_url="http://test",
        auth=BearerAuth("wrong-token"),
        httpx_transport=httpx.ASGITransport(app=mock_app),
        sleep=sleeper,
    )
    connector = PulseAdsConnector(bad)
    with pytest.raises(AuthError):
        _ = [c async for c in connector.get_records()]
    await connector.aclose()
    # 401 is NOT retried.
    assert sleeper.delays == []


async def test_circuit_breaker_opens(sleeper) -> None:  # type: ignore[no-untyped-def]
    # Force repeated 429s so retries are exhausted and the breaker trips.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mock_app), base_url="http://test"
    ) as client:
        await client.post("/pulseads/_arm_rate_limit", params={"count": 999})

    config = ConnectorConfig(
        base_url="http://test",
        auth=BearerAuth("pulse-demo-token"),
        httpx_transport=httpx.ASGITransport(app=mock_app),
        retry=RetryPolicy(max_attempts=2),
        breaker=CircuitBreaker(threshold=3, cooldown=999.0),
        sleep=sleeper,
    )
    connector = PulseAdsConnector(config)

    # Drive failures until the breaker opens and fails fast.
    opened = False
    for _ in range(10):
        try:
            _ = [c async for c in connector.get_records()]
        except CircuitOpenError:
            opened = True
            break
        except Exception:  # noqa: BLE001 - rate-limit/upstream errors expected
            continue
    await connector.aclose()
    assert opened
