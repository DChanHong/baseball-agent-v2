from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from app.domains.baseball.tool.get_weather_context.handler import (
    GetWeatherContextToolHandler,
)
from app.domains.baseball.tool.get_weather_context.kma_client import (
    KmaClient,
    KmaForecastResponse,
    latest_ultra_short_nowcast_base,
    latest_vilage_forecast_base,
)
from app.domains.baseball.tool.get_weather_context.schemas import (
    GetWeatherContextToolInput,
)

KST = ZoneInfo("Asia/Seoul")
FIXED_NOW = datetime(2026, 8, 3, 9, 50, tzinfo=KST)


class FakeKmaClient:
    def __init__(self) -> None:
        self.nowcast_called = False
        self.vilage_forecast_called = False

    async def get_ultra_short_nowcast(self, *, nx: int, ny: int, now: datetime):
        self.nowcast_called = True
        return KmaForecastResponse(
            api_name="기상청 초단기실황",
            base_date="20260803",
            base_time="0900",
            items=[
                {"category": "T1H", "obsrValue": "29.2"},
                {"category": "RN1", "obsrValue": "0"},
                {"category": "PTY", "obsrValue": "0"},
                {"category": "REH", "obsrValue": "65"},
                {"category": "WSD", "obsrValue": "2.4"},
            ],
        )

    async def get_vilage_forecast(self, *, nx: int, ny: int, now: datetime):
        self.vilage_forecast_called = True
        return KmaForecastResponse(
            api_name="기상청 단기예보",
            base_date="20260803",
            base_time="0800",
            items=[
                {
                    "category": "TMP",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "31",
                },
                {
                    "category": "POP",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "70",
                },
                {
                    "category": "PCP",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "1.0mm",
                },
                {
                    "category": "PTY",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "1",
                },
                {
                    "category": "SKY",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "4",
                },
                {
                    "category": "REH",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "82",
                },
                {
                    "category": "WSD",
                    "fcstDate": "20260804",
                    "fcstTime": "1900",
                    "fcstValue": "3.1",
                },
            ],
        )


def test_latest_ultra_short_nowcast_base_uses_previous_hour_before_45_minutes():
    now = datetime(2026, 8, 3, 9, 38, tzinfo=KST)

    assert latest_ultra_short_nowcast_base(now) == datetime(
        2026, 8, 3, 8, 0, tzinfo=KST
    )


def test_latest_vilage_forecast_base_waits_for_publish_buffer():
    now = datetime(2026, 8, 3, 8, 10, tzinfo=KST)

    assert latest_vilage_forecast_base(now) == datetime(
        2026, 8, 3, 5, 0, tzinfo=KST
    )


@pytest.mark.asyncio
async def test_kma_client_requires_service_key():
    client = KmaClient(
        endpoint="https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0",
        service_key="",
    )

    with pytest.raises(ValueError, match="KMA_SERVICE_KEY is required"):
        await client.get_ultra_short_nowcast(nx=61, ny=126, now=FIXED_NOW)


@pytest.mark.asyncio
async def test_get_weather_context_rejects_dates_outside_supported_range():
    handler = GetWeatherContextToolHandler(
        kma_client=FakeKmaClient(),
        now_provider=lambda: FIXED_NOW,
    )

    result = await handler.execute(
        GetWeatherContextToolInput(
            stadium_id="SAJIK",
            date=date(2026, 8, 7),
            time=time(18, 30),
        )
    )

    assert result.supported is False
    assert "weather_query_supported_only_from_today_to_three_days_later" in result.limitations
    assert "long_range_weather_not_supported" in result.limitations


@pytest.mark.asyncio
async def test_get_weather_context_builds_visit_condition_from_forecast():
    fake_client = FakeKmaClient()
    handler = GetWeatherContextToolHandler(
        kma_client=fake_client,
        now_provider=lambda: FIXED_NOW,
    )

    result = await handler.execute(
        GetWeatherContextToolInput(
            stadium_id="SAJIK",
            date=date(2026, 8, 4),
            time=time(18, 30),
        )
    )

    assert result.supported is True
    assert fake_client.vilage_forecast_called is True
    assert fake_client.nowcast_called is False
    assert result.weather is not None
    assert result.weather.temperature_c == 31
    assert result.weather.precipitation_probability == 70
    assert result.weather.precipitation_mm == 1.0
    assert result.visit_condition.level == "bad"
    assert "precipitation_probability_high" in result.visit_condition.reasons
    assert "weather_forecast_not_game_cancellation_decision" in result.limitations
    assert "seat_specific_comfort_not_supported" in result.limitations


@pytest.mark.asyncio
async def test_get_weather_context_keeps_dome_context_for_gocheok():
    handler = GetWeatherContextToolHandler(
        kma_client=FakeKmaClient(),
        now_provider=lambda: FIXED_NOW,
    )

    result = await handler.execute(
        GetWeatherContextToolInput(
            stadium_id="GOCHEOK",
            date=date(2026, 8, 4),
            time=time(18, 30),
        )
    )

    assert result.visit_condition.level == "caution"
    assert "dome_stadium_weather_exposure_limited" in result.visit_condition.reasons


@pytest.mark.asyncio
async def test_get_weather_context_uses_nowcast_for_current_query():
    fake_client = FakeKmaClient()
    handler = GetWeatherContextToolHandler(
        kma_client=fake_client,
        now_provider=lambda: FIXED_NOW,
    )

    result = await handler.execute(
        GetWeatherContextToolInput(
            stadium_id="SAJIK",
            date=date(2026, 8, 3),
            time=time(9, 30),
        )
    )

    assert result.supported is True
    assert fake_client.nowcast_called is True
    assert fake_client.vilage_forecast_called is False
    assert result.source is not None
    assert result.source.api == "기상청 초단기실황"
    assert result.weather is not None
    assert result.weather.temperature_c == 29.2
