"""TODO: token-aware chunker with overlap."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def chunk_tokens(tokens: list[T], chunk_size: int, overlap: int) -> list[list[T]]:
    """Split tokens into overlapping chunks — NOT IMPLEMENTED."""
    return [tokens]
