from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from datetime import time as Time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

WeatherPurpose = Literal["game_weather", "visit_weather"]
WeatherConditionLevel = Literal["good", "caution", "bad", "unsupported"]


class GetWeatherContextToolInput(BaseModel):
    """LLM이 구장 기준 날씨 context를 조회할 때 사용하는 tool 입력입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str = Field(description="KBO stadium id. Example: SAJIK.")
    date: Date = Field(description="Weather target date in YYYY-MM-DD format.")
    time: Time | None = Field(
        default=None,
        description="Optional target time. When omitted, current KST time is used for today.",
    )
    purpose: WeatherPurpose = Field(default="visit_weather")

    @field_validator("stadium_id")
    @classmethod
    def normalize_stadium_id(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("stadium_id cannot be blank")
        return normalized


class WeatherContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature_c: float | None
    precipitation_probability: int | None
    precipitation_mm: float | None
    precipitation_type: str | None
    sky: str | None
    wind_speed_mps: float | None
    humidity_percent: int | None


class VisitCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: WeatherConditionLevel
    reasons: list[str]
    tips: list[str]


class WeatherSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["KMA"]
    base_time: datetime | None
    api: str


class GetWeatherContextToolResult(BaseModel):
    """LLM에 돌려줄 구장 기준 날씨 context tool 결과입니다."""

    model_config = ConfigDict(extra="forbid")

    supported: bool
    stadium_id: str
    stadium_name: str | None
    date: Date
    time: Time | None
    weather: WeatherContext | None
    visit_condition: VisitCondition
    source: WeatherSource | None
    limitations: list[str]
