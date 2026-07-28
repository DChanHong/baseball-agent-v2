from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.baseball.domain.entities import KboGame
from app.domains.baseball.infrastructure.mappers import KboGameMapper
from app.domains.baseball.infrastructure.models import KboGameModel


class SqlAlchemyKboGameRepository:
    """PostgreSQL을 사용하는 KBO 경기 조회 Repository 구현체입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_games(
        self,
        *,
        team_id: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[KboGame]:
        """조건에 맞는 KBO 경기 일정을 조회합니다."""

        statement = select(KboGameModel)

        if team_id is not None:
            normalized_team_id = team_id.strip().upper()
            statement = statement.where(
                or_(
                    KboGameModel.home_team_id == normalized_team_id,
                    KboGameModel.away_team_id == normalized_team_id,
                )
            )

        if date_from is not None:
            statement = statement.where(KboGameModel.game_date >= date_from)

        if date_to is not None:
            statement = statement.where(KboGameModel.game_date <= date_to)

        statement = statement.order_by(
            KboGameModel.game_date.asc(),
            KboGameModel.start_time.asc().nullslast(),
            KboGameModel.home_team_id.asc(),
        )

        result = await self._session.execute(statement)
        models = result.scalars().all()

        return [KboGameMapper.to_domain(model) for model in models]
