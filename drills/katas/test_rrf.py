"""Kata 4: Reciprocal Rank Fusion."""

from __future__ import annotations

import pytest

from drills.katas.rrf import reciprocal_rank_fusion


def test_rrf_combines_rankings() -> None:
    list_a = ["d1", "d2", "d3"]
    list_b = ["d3", "d1", "d2"]
    fused = reciprocal_rank_fusion([list_a, list_b], k=60)
    assert fused == ["d1", "d3", "d2"]
