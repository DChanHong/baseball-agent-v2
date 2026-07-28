from app.domains.baseball.domain.repositories import KboGameRepository
from app.domains.baseball.service.dto import (
    KboGameResultDto,
    ListKboGamesQuery,
)


class ListKboGamesService:
    """KBO 경기 일정을 조회하는 유스케이스입니다."""

    def __init__(self, repository: KboGameRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        query: ListKboGamesQuery,
    ) -> list[KboGameResultDto]:
        """조건에 맞는 KBO 경기 일정을 조회합니다."""

        games = await self._repository.list_games(
            team_id=query.team_id,
            date_from=query.effective_date_from,
            date_to=query.effective_date_to,
        )

        return [KboGameResultDto.from_entity(game) for game in games]
