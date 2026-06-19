"""Pagination across multiple pages for both cursor and offset styles."""

from __future__ import annotations

from mock_apis.data import NOVAREACH_CAMPAIGNS, PULSEADS_CAMPAIGNS


async def test_pulseads_cursor_pagination(make_connector) -> None:  # type: ignore[no-untyped-def]
    connector = make_connector("pulseads")
    records = [c async for c in connector.get_records()]
    await connector.aclose()

    assert len(records) == len(PULSEADS_CAMPAIGNS)
    ids = [r.id for r in records]
    assert ids == [c["campaign_id"] for c in PULSEADS_CAMPAIGNS]
    # Normalization mapped partner-specific fields onto the domain model.
    first = records[0]
    assert first.partner == "pulseads"
    assert first.name == "Summer Sale"
    assert first.status == "active"
    assert first.spend == 125.0


async def test_novareach_offset_pagination(make_connector) -> None:  # type: ignore[no-untyped-def]
    connector = make_connector("novareach")
    records = [c async for c in connector.get_records()]
    await connector.aclose()

    assert len(records) == len(NOVAREACH_CAMPAIGNS)
    assert records[0].name == "Brand Awareness"
    assert records[0].metric == 10_000
    assert {r.status for r in records} == {"active", "paused", "archived"}
