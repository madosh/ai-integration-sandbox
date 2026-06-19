"""Structured JSON logging.

A tiny, dependency-free structured logger. Each record is emitted as a single JSON
line with a stable schema so logs are greppable and machine-parseable. Extra
context is passed via ``logger.info("msg", extra={"context": {...}})``.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update(context)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger, configuring structured output on first use."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)


def log_context(logger: logging.Logger, level: int, msg: str, /, **context: Any) -> None:
    """Log ``msg`` with a structured ``context`` dict."""
    logger.log(level, msg, extra={"context": context})
