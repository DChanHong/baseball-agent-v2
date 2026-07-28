from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.baseball.domain.enums import KboGameStatus


class KboGameResponse(BaseModel):
    """KBO 경기 HTTP 응답 Schema입니다."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    season_year: int
    source_game_id: str | None
    internal_game_key: str
    game_date: date
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
