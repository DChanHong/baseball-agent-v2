import logging

from app.domains.baseball.service.dto import ListKboGamesQuery
from app.domains.baseball.service.services import ListKboGamesService
from app.domains.baseball.tool.find_kbo_game.schemas import (
    FindKboGameToolInput,
    FindKboGameToolResult,
    KboGameToolResultItem,
)

logger = logging.getLogger(__name__)


class FindKboGameToolHandler:
    """LLM의 find_kbo_game tool 호출을 처리합니다."""

    def __init__(self, service: ListKboGamesService) -> None:
        self._service = service

    async def execute(
        self,
        tool_input: FindKboGameToolInput,
    ) -> FindKboGameToolResult:
        """KBO 경기 조회 tool을 실행합니다."""

        logger.info(
            "find_kbo_game tool started team_id=%s date=%s date_from=%s date_to=%s",
            tool_input.team_id,
            tool_input.date,
            tool_input.date_from,
            tool_input.date_to,
        )

        query = ListKboGamesQuery(
            team_id=tool_input.team_id,
            date=tool_input.date,
            date_from=tool_input.date_from,
            date_to=tool_input.date_to,
        )

        try:
            games = await self._service.execute(query)
        except Exception:
            logger.exception("find_kbo_game tool failed")
            raise

        result_items = [
            KboGameToolResultItem.model_validate(game, from_attributes=True)
            for game in games
        ]

        logger.info(
            "find_kbo_game tool completed team_id=%s count=%d",
            tool_input.team_id,
            len(result_items),
        )

        return FindKboGameToolResult(
            total=len(result_items),
            games=result_items,
        )
