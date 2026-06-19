"""Corpus loader: read mock company docs and chunk them."""

from __future__ import annotations

from pathlib import Path

from aih.rag.chunking import chunk_document
from aih.rag.models import Chunk

CORPUS_DIR = Path(__file__).parent / "corpus"


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def load_chunks(
    corpus_dir: Path | None = None, *, chunk_size: int = 120, overlap: int = 24
) -> list[Chunk]:
    """Load every ``*.md`` doc in the corpus and return token-aware chunks."""
    directory = corpus_dir or CORPUS_DIR
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        doc_id = path.stem
        title = _title_of(text, doc_id)
        chunks.extend(
            chunk_document(
                doc_id,
                text,
                chunk_size=chunk_size,
                overlap=overlap,
                metadata={"title": title, "source": path.name},
            )
        )
    return chunks
