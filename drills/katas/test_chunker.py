"""Kata 3: token-aware chunker."""

from __future__ import annotations

import pytest

from drills.katas.chunker import chunk_tokens


def test_chunk_with_overlap() -> None:
    tokens = list(range(20))
    chunks = chunk_tokens(tokens, chunk_size=8, overlap=2)
    assert chunks[0] == list(range(8))
    assert chunks[1] == list(range(6, 14))
    assert chunks[-1][-1] == 19
