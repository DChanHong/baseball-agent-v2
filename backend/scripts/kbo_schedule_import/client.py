from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

KBO_SCHEDULE_ENDPOINT = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
KBO_SCHEDULE_PAGE_URL = "https://www.koreabaseball.com/Schedule/Schedule.aspx"


@dataclass(frozen=True, slots=True)
class KboScheduleRequest:
    """KBO schedule API request parameters."""

    season_year: int
    month: int

    def to_form_data(self) -> dict[str, str]:
        return {
            "leId": "1",
            "srIdList": "0,9,6",
            "seasonId": str(self.season_year),
            "gameMonth": f"{self.month:02d}",
            "teamId": "",
        }


class KboScheduleClient:
    """Thin HTTP client for KBO schedule table data."""

    def __init__(
        self,
        *,
        endpoint: str = KBO_SCHEDULE_ENDPOINT,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    async def fetch_month(self, request: KboScheduleRequest) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.koreabaseball.com",
            "Referer": KBO_SCHEDULE_PAGE_URL,
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                self._endpoint,
                data=request.to_form_data(),
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        return unwrap_kbo_schedule_response(payload)


def unwrap_kbo_schedule_response(payload: Any) -> dict[str, Any]:
    """Return the schedule payload regardless of ASMX wrapper shape."""

    if isinstance(payload, dict) and "d" in payload:
        wrapped = payload["d"]
        if isinstance(wrapped, str):
            parsed = json.loads(wrapped)
            if not isinstance(parsed, dict):
                raise TypeError("KBO schedule response wrapper is not an object.")
            return parsed
        if isinstance(wrapped, dict):
            return wrapped

    if isinstance(payload, dict):
        return payload

    raise TypeError("KBO schedule response is not an object.")
