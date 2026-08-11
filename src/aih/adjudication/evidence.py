"""Deterministic evidence gathering.

Reads the finding's source file through a :class:`SourceProvider` and extracts a window of
lines around the reported line. Pure Python, no model calls. The returned text is data: it is
never interpreted as instructions by anything downstream.
"""

from __future__ import annotations

from aih.adjudication.models import EvidenceSpan, Finding
from aih.adjudication.sources import SourceProvider

DEFAULT_CONTEXT_LINES = 5


def gather_evidence(
    finding: Finding,
    source: SourceProvider,
    *,
    context_lines: int = DEFAULT_CONTEXT_LINES,
) -> list[EvidenceSpan]:
    """Return evidence spans for ``finding``.

    A single window of ``+/- context_lines`` around ``finding.line`` is returned. If the file
    cannot be read, an empty list is returned — the caller (policy gate) treats "no evidence"
    as a reason to escalate, never to dismiss.
    """
    text = source.read_file(finding.file_path)
    if text is None:
        return []

    lines = text.splitlines()
    if not lines:
        return []

    # Clamp the window to the file. Lines are 1-indexed to match static-analysis tools.
    start = max(1, finding.line - context_lines)
    end = min(len(lines), finding.line + context_lines)
    window = "\n".join(lines[start - 1 : end])

    return [
        EvidenceSpan(
            file_path=finding.file_path,
            start_line=start,
            end_line=end,
            text=window,
        )
    ]
