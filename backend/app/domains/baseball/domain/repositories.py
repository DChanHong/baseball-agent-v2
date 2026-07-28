from datetime import date
from typing import Protocol

from app.domains.baseball.domain.entities import KboGame


class KboGameRepository(Protocol):
    """KBO 경기 조회 저장소의 도메인 인터페이스입니다."""

    async def list_games(
        self,
        *,
        team_id: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[KboGame]:
        """조건에 맞는 KBO 경기 일정을 조회합니다."""

        ...
