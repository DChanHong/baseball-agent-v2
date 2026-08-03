from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx

KST = ZoneInfo("Asia/Seoul")
VILAGE_BASE_TIMES = [
    time(2, 0),
    time(5, 0),
    time(8, 0),
    time(11, 0),
    time(14, 0),
    time(17, 0),
    time(20, 0),
    time(23, 0),
]


@dataclass(frozen=True)
class KmaForecastResponse:
    api_name: str
    base_date: str
    base_time: str
    items: list[dict[str, object]]

    @property
    def base_datetime(self) -> datetime:
        return datetime.strptime(
            self.base_date + self.base_time,
            "%Y%m%d%H%M",
        ).replace(tzinfo=KST)


class KmaClient:
    """Small client for KMA VilageFcstInfoService_2.0."""

    def __init__(
        self,
        *,
        endpoint: str,
        service_key: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._service_key = service_key.strip()
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def get_ultra_short_nowcast(
        self,
        *,
        nx: int,
        ny: int,
        now: datetime | None = None,
    ) -> KmaForecastResponse:
        base_dt = latest_ultra_short_nowcast_base(now or datetime.now(KST))
        items = await self._request_items(
            path="getUltraSrtNcst",
            base_date=base_dt.strftime("%Y%m%d"),
            base_time=base_dt.strftime("%H%M"),
            nx=nx,
            ny=ny,
        )
        return KmaForecastResponse(
            api_name="기상청 초단기실황",
            base_date=base_dt.strftime("%Y%m%d"),
            base_time=base_dt.strftime("%H%M"),
            items=items,
        )

    async def get_vilage_forecast(
        self,
        *,
        nx: int,
        ny: int,
        now: datetime | None = None,
    ) -> KmaForecastResponse:
        base_dt = latest_vilage_forecast_base(now or datetime.now(KST))
        items = await self._request_items(
            path="getVilageFcst",
            base_date=base_dt.strftime("%Y%m%d"),
            base_time=base_dt.strftime("%H%M"),
            nx=nx,
            ny=ny,
        )
        return KmaForecastResponse(
            api_name="기상청 단기예보",
            base_date=base_dt.strftime("%Y%m%d"),
            base_time=base_dt.strftime("%H%M"),
            items=items,
        )

    async def _request_items(
        self,
        *,
        path: str,
        base_date: str,
        base_time: str,
        nx: int,
        ny: int,
    ) -> list[dict[str, object]]:
        if not self._service_key:
            raise ValueError("KMA_SERVICE_KEY is required")

        params = {
            "ServiceKey": self._service_key,
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        }
        url = f"{self._endpoint}/{path}"

        if self._http_client is not None:
            response = await self._http_client.get(url, params=params)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url, params=params)

        response.raise_for_status()
        payload = response.json()
        body = payload.get("response", {}).get("body", {})
        header = payload.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        if result_code and result_code != "00":
            result_msg = header.get("resultMsg") or "KMA API error"
            raise ValueError(f"KMA API error {result_code}: {result_msg}")

        items = body.get("items", {}).get("item", [])
        if not isinstance(items, list):
            raise TypeError("KMA API response items must be a list")
        return [item for item in items if isinstance(item, dict)]


def latest_ultra_short_nowcast_base(now: datetime) -> datetime:
    kst_now = now.astimezone(KST)
    if kst_now.minute < 45:
        kst_now = kst_now - timedelta(hours=1)
    return kst_now.replace(minute=0, second=0, microsecond=0)


def latest_vilage_forecast_base(now: datetime) -> datetime:
    kst_now = now.astimezone(KST)
    usable_time = (
        datetime.combine(kst_now.date(), kst_now.time(), tzinfo=KST)
        - timedelta(minutes=20)
    )

    for base_time in reversed(VILAGE_BASE_TIMES):
        candidate = datetime.combine(usable_time.date(), base_time, tzinfo=KST)
        if candidate <= usable_time:
            return candidate

    previous_day = usable_time.date() - timedelta(days=1)
    return datetime.combine(previous_day, VILAGE_BASE_TIMES[-1], tzinfo=KST)


def is_within_supported_forecast_range(target_date: Date, today: Date) -> bool:
    return today <= target_date <= today + timedelta(days=3)
