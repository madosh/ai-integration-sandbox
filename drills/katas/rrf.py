"""TODO: Reciprocal Rank Fusion."""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Merge ranked doc id lists via RRF — NOT IMPLEMENTED."""
    return rankings[0] if rankings else []
