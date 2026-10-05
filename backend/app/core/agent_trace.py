"""Content-free, task-local instrumentation for an agent turn."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)
_current_trace: ContextVar[str | None] = ContextVar("agent_trace_id", default=None)


def emit_trace(trace_id: str, event: str, **fields: Any) -> None:
    """Callers supply only operational fields, never prompts or exception text."""
    record = {
        "schema_version": 1,
        "trace_id": trace_id,
        "event": event,
        "timestamp": datetime.now(UTC).isoformat(),
        **fields,
    }
    logger.info("agent_trace %s", json.dumps(record, ensure_ascii=False))


@contextmanager
def trace_scope(trace_id: str) -> Iterator[None]:
    token = _current_trace.set(trace_id)
    try:
        yield
    finally:
        _current_trace.reset(token)


@contextmanager
def trace_stage(stage: str, **fields: Any) -> Iterator[dict[str, Any]]:
    """Measure a stage; outside an agent turn this is an instrumentation no-op."""
    trace_id = _current_trace.get()
    details: dict[str, Any] = {}
    started = perf_counter()
    if trace_id is not None:
        emit_trace(trace_id, f"{stage}.started", **fields)
    try:
        yield details
    except BaseException as exc:
        details.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        if trace_id is not None:
            status = details.pop("status", "completed")
            emit_trace(
                trace_id,
                f"{stage}.{status}",
                duration_ms=round((perf_counter() - started) * 1000, 3),
                **fields,
                **details,
            )


def retrieval_details(items: list[Any]) -> dict[str, Any]:
    return {
        "result_count": len(items),
        "answerable": bool(items),
        "chunk_ids": [item.chunk_id for item in items],
        "distances": [item.distance for item in items],
    }
