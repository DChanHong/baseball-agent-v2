from __future__ import annotations

from datetime import date as Date
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.baseball.domain.enums import KboGameStatus


class FindKboGameToolInput(BaseModel):
    """LLM이 KBO 경기 일정을 조회할 때 사용하는 tool 입력입니다."""

    team_id: str | None = Field(
        default=None,
        description="KBO team id. Examples: LG, DOOSAN, KIWOOM, SSG, KIA, SAMSUNG, LOTTE, NC, HANWHA, KT.",
    )
    date: Date | None = Field(
        default=None,
        description="Single game date in YYYY-MM-DD format. Do not use with date_from/date_to.",
    )
    date_from: Date | None = Field(
        default=None,
        description="Start date in YYYY-MM-DD format for range lookup.",
    )
    date_to: Date | None = Field(
        default=None,
        description="End date in YYYY-MM-DD format for range lookup.",
    )


class KboGameToolResultItem(BaseModel):
    """LLM tool 결과에 포함되는 단일 KBO 경기입니다."""

    id: UUID
    season_year: int
    source_game_id: str | None
    internal_game_key: str
    game_date: Date
    start_time: time | None
    starts_at: datetime | None
    away_team_id: str
    home_team_id: str
    stadium_id: str
    away_team_name: str
    home_team_name: str
    stadium_name: str
    game_status: KboGameStatus
    status_reason: str | None
    away_score: int | None
    home_score: int | None
    source_name: str
    source_url: str
    source_collected_at: datetime


class FindKboGameToolResult(BaseModel):
    """LLM에 돌려줄 KBO 경기 조회 tool 결과입니다."""

    total: int
    games: list[KboGameToolResultItem]
