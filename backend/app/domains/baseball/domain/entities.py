from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from app.domains.baseball.domain.enums import KboGameStatus


@dataclass(frozen=True, slots=True)
class KboGame:
    """KBO 경기 일정을 나타내는 순수 도메인 객체입니다."""

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
    created_at: datetime
    updated_at: datetime
