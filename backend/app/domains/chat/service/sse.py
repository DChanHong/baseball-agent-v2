from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def encode_sse_event(event: str, data: BaseModel | Mapping[str, Any]) -> str:
    """Encode a named SSE event with a JSON payload."""

    if isinstance(data, BaseModel):
        payload = data.model_dump(mode="json")
    else:
        payload = dict(data)

    return (
        f"event: {event}\n"
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )
