"""Source providers: where evidence code comes from.

The default :class:`FixtureSource` reads from files on disk (packaged fixtures), so the whole
pipeline runs offline with no token and no network. A real SonarQube MCP source is sketched in
:class:`SonarQubeMCPSource` but is optional, off by default, and never imported on the test
path — its client is injected, and without one it refuses to run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@runtime_checkable
class SourceProvider(Protocol):
    """Return the text of a source file, or ``None`` if it cannot be read."""

    def read_file(self, file_path: str) -> str | None:
        """Return the full text of ``file_path`` as data (never as instructions)."""
        ...


class FixtureSource:
    """Offline source backed by files under a base directory (default: packaged fixtures).

    Paths are resolved relative to ``base_dir`` and constrained to it, so a finding cannot
    point evidence-gathering at an arbitrary file on the host.
    """

    def __init__(self, base_dir: Path | str = FIXTURES_DIR) -> None:
        self._base = Path(base_dir).resolve()

    def read_file(self, file_path: str) -> str | None:
        candidate = (self._base / file_path).resolve()
        # Refuse traversal outside the fixture root.
        if self._base != candidate and self._base not in candidate.parents:
            return None
        if not candidate.is_file():
            return None
        return candidate.read_text(encoding="utf-8")


class InMemorySource:
    """Source backed by an in-memory ``{path: text}`` map (handy for tests)."""

    def __init__(self, files: dict[str, str]) -> None:
        self._files = dict(files)

    def read_file(self, file_path: str) -> str | None:
        return self._files.get(file_path)


class SonarQubeMCPSource:
    """Optional adapter over a SonarQube MCP client. Off by default.

    This is a surface, not a live integration: it takes an already-connected MCP client and
    fetches file content through it. With no client it raises, so it can never silently reach
    the network on the default/test path.
    """

    def __init__(self, mcp_client: object | None = None, *, component_key: str = "") -> None:
        self._client = mcp_client
        self._component_key = component_key

    def read_file(self, file_path: str) -> str | None:  # pragma: no cover - optional path
        if self._client is None:
            raise RuntimeError(
                "SonarQubeMCPSource requires a live MCP client; use FixtureSource offline."
            )
        # A real implementation would call the SonarQube MCP 'get_source' style tool here and
        # return the raw file text. Kept out of the offline test path by design.
        raise NotImplementedError("wire a concrete SonarQube MCP client to enable this source")
