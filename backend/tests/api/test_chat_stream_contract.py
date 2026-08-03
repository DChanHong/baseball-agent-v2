from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from app.domains.chat.controller.schemas import (
    DoneEvent,
    ToolCompletedEvent,
)
from app.domains.chat.service.sse import encode_sse_event


def test_encode_sse_event_uses_named_event_and_compact_json_data():
    encoded = encode_sse_event(
        "done",
        DoneEvent(conversation_id=UUID("00000000-0000-0000-0000-000000000001")),
    )

    assert encoded.startswith("event: done\n")
    assert encoded.endswith("\n\n")
    data_line = encoded.splitlines()[1]
    assert data_line.startswith("data: ")
    assert json.loads(data_line.removeprefix("data: ")) == {
        "conversation_id": "00000000-0000-0000-0000-000000000001"
    }


def test_tool_completed_event_keeps_tool_specific_result_payload_open():
    event = ToolCompletedEvent(
        tool_call_id="tool_01",
        name="get_weather_context",
        status="completed",
        input={
            "stadium_id": "SAJIK",
            "date": "2026-08-03",
            "time": None,
            "purpose": "visit_weather",
        },
        result={
            "supported": True,
            "stadium_id": "SAJIK",
            "source": {
                "provider": "KMA",
                "base_time": datetime(2026, 8, 3, 9, tzinfo=UTC),
                "api": "기상청 초단기실황",
            },
            "limitations": ["weather_forecast_not_game_cancellation_decision"],
        },
    )

    payload = event.model_dump(mode="json")

    assert payload["name"] == "get_weather_context"
    assert payload["status"] == "completed"
    assert payload["result"]["source"]["provider"] == "KMA"
    assert payload["error"] is None
