from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domains.baseball.tool.get_weather_context.kma_client import (
    KmaClient,
    KmaForecastResponse,
    is_within_supported_forecast_range,
)
from app.domains.baseball.tool.get_weather_context.schemas import (
    GetWeatherContextToolInput,
    GetWeatherContextToolResult,
    VisitCondition,
    WeatherContext,
    WeatherSource,
)
from app.domains.baseball.tool.get_weather_context.stadium_grid import (
    get_stadium_weather_grid,
)

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
SKY_LABELS = {
    "1": "clear",
    "3": "mostly_cloudy",
    "4": "cloudy",
}
PTY_LABELS = {
    "0": "none",
    "1": "rain",
    "2": "rain_snow",
    "3": "snow",
    "5": "raindrops",
    "6": "raindrops_snow_flurries",
    "7": "snow_flurries",
}


class GetWeatherContextToolHandler:
    """LLM의 get_weather_context tool 호출을 처리합니다."""

    def __init__(self, kma_client: KmaClient) -> None:
        self._kma_client = kma_client

    async def execute(
        self,
        tool_input: GetWeatherContextToolInput,
    ) -> GetWeatherContextToolResult:
        logger.info(
            "get_weather_context tool started stadium_id=%s date=%s time=%s",
            tool_input.stadium_id,
            tool_input.date,
            tool_input.time,
        )

        grid = get_stadium_weather_grid(tool_input.stadium_id)
        if grid is None:
            return _unsupported_result(
                tool_input,
                limitations=["stadium_weather_grid_not_supported"],
            )

        now = datetime.now(KST)
        if not is_within_supported_forecast_range(tool_input.date, now.date()):
            return _unsupported_result(
                tool_input,
                stadium_name=grid.stadium_name,
                limitations=[
                    "weather_query_supported_only_from_today_to_three_days_later",
                    "past_weather_not_supported",
                    "long_range_weather_not_supported",
                ],
            )

        target_time = tool_input.time
        if target_time is None and tool_input.date == now.date():
            target_time = now.time().replace(second=0, microsecond=0)

        try:
            if tool_input.date == now.date() and _is_current_query(target_time, now):
                response = await self._kma_client.get_ultra_short_nowcast(
                    nx=grid.nx,
                    ny=grid.ny,
                    now=now,
                )
                weather = _weather_from_nowcast(response)
            else:
                response = await self._kma_client.get_vilage_forecast(
                    nx=grid.nx,
                    ny=grid.ny,
                    now=now,
                )
                weather = _weather_from_vilage_forecast(
                    response,
                    target_date=tool_input.date,
                    target_time=target_time,
                )
        except Exception:
            logger.exception("get_weather_context tool failed")
            raise

        limitations = [
            "weather_forecast_not_game_cancellation_decision",
            "seat_specific_comfort_not_supported",
            "weather_query_supported_only_from_today_to_three_days_later",
        ]
        if weather is None:
            limitations.append("weather_data_not_found_for_requested_time")
            visit_condition = VisitCondition(
                level="unsupported",
                reasons=["weather_data_not_found"],
                tips=["조회 가능한 시간대의 날씨만 확인할 수 있어요."],
            )
        else:
            visit_condition = _build_visit_condition(weather, is_dome=grid.is_dome)

        logger.info(
            "get_weather_context tool completed stadium_id=%s supported=%s",
            tool_input.stadium_id,
            weather is not None,
        )
        return GetWeatherContextToolResult(
            supported=weather is not None,
            stadium_id=grid.stadium_id,
            stadium_name=grid.stadium_name,
            date=tool_input.date,
            time=target_time,
            weather=weather,
            visit_condition=visit_condition,
            source=WeatherSource(
                provider="KMA",
                base_time=response.base_datetime,
                api=response.api_name,
            ),
            limitations=limitations,
        )


def _unsupported_result(
    tool_input: GetWeatherContextToolInput,
    *,
    stadium_name: str | None = None,
    limitations: list[str],
) -> GetWeatherContextToolResult:
    return GetWeatherContextToolResult(
        supported=False,
        stadium_id=tool_input.stadium_id,
        stadium_name=stadium_name,
        date=tool_input.date,
        time=tool_input.time,
        weather=None,
        visit_condition=VisitCondition(
            level="unsupported",
            reasons=limitations,
            tips=["기상청 단기예보 조회서비스에서 조회 가능한 기간의 날씨만 확인할 수 있어요."],
        ),
        source=None,
        limitations=limitations,
    )


def _is_current_query(target_time: time | None, now: datetime) -> bool:
    if target_time is None:
        return True
    target_hour = target_time.hour
    return target_hour <= now.hour


def _weather_from_nowcast(response: KmaForecastResponse) -> WeatherContext:
    values = {
        str(item.get("category")): str(item.get("obsrValue"))
        for item in response.items
        if item.get("category") is not None
    }
    return WeatherContext(
        temperature_c=_to_float(values.get("T1H")),
        precipitation_probability=None,
        precipitation_mm=_parse_precipitation(values.get("RN1")),
        precipitation_type=PTY_LABELS.get(values.get("PTY") or ""),
        sky=None,
        wind_speed_mps=_to_float(values.get("WSD")),
        humidity_percent=_to_int(values.get("REH")),
    )


def _weather_from_vilage_forecast(
    response: KmaForecastResponse,
    *,
    target_date,
    target_time: time | None,
) -> WeatherContext | None:
    target_date_text = target_date.strftime("%Y%m%d")
    target_time_text = _select_forecast_time(response, target_date_text, target_time)
    if target_time_text is None:
        return None

    values = {
        str(item.get("category")): str(item.get("fcstValue"))
        for item in response.items
        if str(item.get("fcstDate")) == target_date_text
        and str(item.get("fcstTime")) == target_time_text
        and item.get("category") is not None
    }
    if not values:
        return None

    return WeatherContext(
        temperature_c=_to_float(values.get("TMP")),
        precipitation_probability=_to_int(values.get("POP")),
        precipitation_mm=_parse_precipitation(values.get("PCP")),
        precipitation_type=PTY_LABELS.get(values.get("PTY") or ""),
        sky=SKY_LABELS.get(values.get("SKY") or ""),
        wind_speed_mps=_to_float(values.get("WSD")),
        humidity_percent=_to_int(values.get("REH")),
    )


def _select_forecast_time(
    response: KmaForecastResponse,
    target_date_text: str,
    target_time: time | None,
) -> str | None:
    times = sorted(
        {
            str(item.get("fcstTime"))
            for item in response.items
            if str(item.get("fcstDate")) == target_date_text and item.get("fcstTime")
        }
    )
    if not times:
        return None
    if target_time is None:
        return times[0]

    target_minutes = target_time.hour * 60 + target_time.minute
    for fcst_time in times:
        forecast_minutes = int(fcst_time[:2]) * 60 + int(fcst_time[2:])
        if forecast_minutes >= target_minutes:
            return fcst_time
    return times[-1]


def _build_visit_condition(weather: WeatherContext, *, is_dome: bool) -> VisitCondition:
    reasons: list[str] = []
    tips: list[str] = []
    level = "good"

    if is_dome:
        reasons.append("dome_stadium_weather_exposure_limited")
        tips.append("돔구장은 비의 직접 영향이 제한적이지만 이동 중 날씨는 확인하세요.")

    if weather.precipitation_probability is not None and weather.precipitation_probability >= 60:
        reasons.append("precipitation_probability_high")
        tips.append("우비나 방수 가능한 겉옷을 준비하세요.")
        level = "caution"

    if weather.precipitation_mm is not None and weather.precipitation_mm >= 1.0:
        reasons.append("precipitation_expected")
        tips.append("강수량 예보가 있어 이동 시간과 공식 경기 상태를 함께 확인하세요.")
        level = "bad" if not is_dome else "caution"

    if weather.temperature_c is not None and weather.temperature_c >= 30:
        reasons.append("temperature_high")
        tips.append("수분 보충과 통풍이 잘 되는 옷차림을 준비하세요.")
        level = "bad" if weather.temperature_c >= 33 else max_level(level, "caution")

    if weather.humidity_percent is not None and weather.humidity_percent >= 80:
        reasons.append("humidity_high")
        tips.append("습도가 높아 체감 더위가 커질 수 있어요.")
        level = max_level(level, "caution")

    if weather.wind_speed_mps is not None and weather.wind_speed_mps >= 8:
        reasons.append("wind_speed_high")
        tips.append("강한 바람에 대비해 가벼운 소지품을 잘 챙기세요.")
        level = max_level(level, "caution")

    if not reasons:
        reasons.append("no_significant_weather_risk")
        tips.append("큰 날씨 변수는 낮아 보이지만, 출발 전 최신 예보를 한 번 더 확인하세요.")

    tips.append("실제 경기 진행 여부는 공식 경기 상태나 구단 공지를 함께 확인하세요.")
    return VisitCondition(level=level, reasons=reasons, tips=tips)


def max_level(current: str, candidate: str) -> str:
    rank = {"good": 0, "caution": 1, "bad": 2}
    return candidate if rank[candidate] > rank[current] else current


def _to_float(value: str | None) -> float | None:
    if value is None or value in {"", "강수없음", "적설없음"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    parsed = _to_float(value)
    return int(parsed) if parsed is not None else None


def _parse_precipitation(value: str | None) -> float | None:
    if value is None or value in {"", "강수없음", "강수 없음"}:
        return 0.0
    if "미만" in value:
        return 0.0
    if "~" in value:
        value = value.split("~", maxsplit=1)[0]
    normalized = value.replace("mm", "").strip()
    return _to_float(normalized)
