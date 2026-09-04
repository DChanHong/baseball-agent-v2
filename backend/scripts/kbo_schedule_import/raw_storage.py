from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.kbo_schedule_import.client import (
    KBO_SCHEDULE_ENDPOINT,
    KBO_SCHEDULE_PAGE_URL,
    KboScheduleRequest,
)


@dataclass(frozen=True, slots=True)
class StoredKboScheduleRaw:
    """Metadata for a saved local KBO schedule raw response."""

    file_path: Path
    payload: dict[str, Any]


def build_raw_snapshot_payload(
    *,
    request: KboScheduleRequest,
    collected_at: datetime,
    response_json: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_name": "KBO Schedule.asmx/GetScheduleList",
        "source_url": KBO_SCHEDULE_PAGE_URL,
        "endpoint": KBO_SCHEDULE_ENDPOINT,
        "request_params": request.to_form_data(),
        "collected_at": collected_at.isoformat(),
        "response_json": response_json,
    }


def save_raw_schedule_response(
    *,
    raw_root: Path,
    request: KboScheduleRequest,
    collected_at: datetime,
    response_json: dict[str, Any],
) -> StoredKboScheduleRaw:
    payload = build_raw_snapshot_payload(
        request=request,
        collected_at=collected_at,
        response_json=response_json,
    )
    file_path = raw_root / str(request.season_year) / f"{request.month:02d}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return StoredKboScheduleRaw(file_path=file_path, payload=payload)
