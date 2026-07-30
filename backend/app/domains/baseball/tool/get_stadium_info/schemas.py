from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GetStadiumInfoToolInput(BaseModel):
    """LLM이 정형 구장 정보를 조회할 때 사용하는 tool 입력입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str | None = Field(
        default=None,
        description="KBO stadium id. Example: SAJIK.",
    )
    team_id: str | None = Field(
        default=None,
        description="KBO team id. Used to resolve the team's home stadium.",
    )

    @field_validator("stadium_id", "team_id")
    @classmethod
    def normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("identifier cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_lookup_key(self) -> GetStadiumInfoToolInput:
        if self.stadium_id is None and self.team_id is None:
            raise ValueError("stadium_id or team_id is required")
        return self


class StadiumInfoItem(BaseModel):
    """정형 DB에서 조회한 KBO 구장 기본 정보입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str
    name_ko: str
    short_name: str
    aliases: list[str]
    city: str | None
    region: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    is_dome: bool | None
    home_team_id: str | None
    home_team_ids: list[str]
    official_url: str | None
    source_url: str | None
    as_of: Date | None
    metadata: dict[str, object]


class GetStadiumInfoToolResult(BaseModel):
    """LLM에 돌려줄 정형 구장 정보 tool 결과입니다."""

    model_config = ConfigDict(extra="forbid")

    found: bool
    stadium: StadiumInfoItem | None
    limitations: list[str]
