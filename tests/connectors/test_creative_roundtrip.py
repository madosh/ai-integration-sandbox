"""Multipart creative upload + download round-trip and idempotent re-upload."""

from __future__ import annotations


async def test_creative_upload_download_roundtrip(make_connector) -> None:  # type: ignore[no-untyped-def]
    connector = make_connector("creativebox")
    content = b"\x89PNG\r\n fake creative bytes"

    result = await connector.push_creative(
        name="banner.png", content=content, content_type="image/png"
    )
    assert result.status == "created"
    assert result.idempotent_hit is False

    meta, downloaded = await connector.get_creative(result.id)
    await connector.aclose()

    assert downloaded == content
    assert meta.name == "banner.png"
    assert meta.content_type == "image/png"
    assert meta.size_bytes == len(content)


async def test_creative_upload_is_idempotent(make_connector) -> None:  # type: ignore[no-untyped-def]
    connector = make_connector("creativebox")
    content = b"same-bytes"

    first = await connector.push_creative(name="a.png", content=content, content_type="image/png")
    second = await connector.push_creative(name="a.png", content=content, content_type="image/png")
    await connector.aclose()

    assert first.id == second.id
    assert second.idempotent_hit is True
    assert second.status == "duplicate"
