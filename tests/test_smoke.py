"""Phase 0 smoke test: the package imports and config loads offline."""

from __future__ import annotations


def test_import_aih() -> None:
    import aih

    assert aih.__version__


def test_settings_offline_defaults() -> None:
    from aih.config import get_settings

    settings = get_settings()
    assert settings.llm_provider == "fake"
    assert settings.embedder == "hash"


async def test_fake_llm_is_deterministic() -> None:
    from aih.llm import FakeLLM
    from aih.llm.base import ChatMessage

    llm = FakeLLM()
    msgs = [ChatMessage(role="user", content="sync campaign data from novareach")]
    a = await llm.complete(msgs)
    b = await llm.complete(msgs)
    assert a.text == b.text


def test_hash_embedder_is_deterministic() -> None:
    from aih.llm import HashEmbedder

    emb = HashEmbedder(dim=64)
    v1 = emb.embed(["hello world"])[0]
    v2 = emb.embed(["hello world"])[0]
    assert v1 == v2
    assert len(v1) == 64
