"""
Structured logging helpers for UltimateSkillOS.

Provides a JSON formatter and a helper to obtain a LoggerAdapter
that automatically injects trace_id, step_id, and correlation_id
into log records.
"""
from __future__ import annotations

import json
import logging
from typing import Any


class JSONFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields if present
        extras = {}
        for k, v in record.__dict__.items():
            if k in ("msg", "args", "levelname", "levelno", "name", "msg"):
                continue
            if k.startswith("_"):
                continue
            if k in ("timestamp", "level", "logger", "message"):
                continue
            extras[k] = v

        if extras:
            payload["extra"] = extras

        return json.dumps(payload, default=str)


def get_logger(name: str, *, trace_id: str | None = None, step_id: str | None = None, correlation_id: str | None = None) -> logging.Logger:
    """
    Return a logger configured with a JSONFormatter and pre-populated extras.

    The returned object is a `logging.LoggerAdapter` whose `extra` will
    include `trace_id`, `step_id`, and `correlation_id` when set.
    """
    logger = logging.getLogger(name)

    # Ensure a handler with JSONFormatter exists (not duplicating handlers)
    if not any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    extra = {}
    if trace_id:
        extra["trace_id"] = trace_id
    if step_id:
        extra["step_id"] = step_id
    if correlation_id:
        extra["correlation_id"] = correlation_id

    return logging.LoggerAdapter(logger, extra)
