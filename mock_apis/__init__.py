"""Local fake partner APIs (ad networks + docs store).

A single FastAPI app simulating multiple partners with deliberately different auth
and pagination conventions, so the connector abstraction has to earn its keep.
See ``specs/connectors.md``. Implemented in Phase 1.
"""

from __future__ import annotations

__all__: list[str] = []
