from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Self
from uuid import UUID

from app.domains.baseball.domain.entities import KboGame
from app.domains.baseball.domain.enums import KboGameStatus


@dataclass(frozen=True, slots=True)
class ListKboGamesQuery:
    """KBO 경기 조회 Service에 전달하는 입력 DTO입니다."""

    team_id: str | None = None
    date: date | None = None
    date_from: date | None = None
    date_to: date | None = None

    def __post_init__(self) -> None:
        if self.team_id is not None and not self.team_id.strip():
            raise ValueError("team_id는 빈 문자열일 수 없습니다.")

        if self.date is not None and (
            self.date_from is not None or self.date_to is not None
        ):
            raise ValueError("date와 date_from/date_to는 함께 사용할 수 없습니다.")

        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from은 date_to보다 늦을 수 없습니다.")

    @property
    def effective_date_from(self) -> date | None:
        return self.date if self.date is not None else self.date_from

    @property
    def effective_date_to(self) -> date | None:
        return self.date if self.date is not None else self.date_to


@dataclass(frozen=True, slots=True)
class KboGameResultDto:
    """Service가 Controller에 반환하는 KBO 경기 결과 DTO입니다."""

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

    @classmethod
    def from_entity(cls, game: KboGame) -> Self:
        """Domain Entity를 Service 결과 DTO로 변환합니다."""

        return cls(
            id=game.id,
            season_year=game.season_year,
            source_game_id=game.source_game_id,
            internal_game_key=game.internal_game_key,
            game_date=game.game_date,
            start_time=game.start_time,
            starts_at=game.starts_at,
            away_team_id=game.away_team_id,
            home_team_id=game.home_team_id,
            stadium_id=game.stadium_id,
            away_team_name=game.away_team_name,
            home_team_name=game.home_team_name,
            stadium_name=game.stadium_name,
            game_status=game.game_status,
            status_reason=game.status_reason,
            away_score=game.away_score,
            home_score=game.home_score,
            source_name=game.source_name,
            source_url=game.source_url,
            source_collected_at=game.source_collected_at,
        )
