import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.baseball.infrastructure.models import (
    KboStadiumModel,
    KboTeamModel,
)
from app.domains.baseball.tool.get_stadium_info.schemas import (
    GetStadiumInfoToolInput,
    GetStadiumInfoToolResult,
    StadiumInfoItem,
)

logger = logging.getLogger(__name__)


class GetStadiumInfoToolHandler:
    """LLM의 get_stadium_info tool 호출을 처리합니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        tool_input: GetStadiumInfoToolInput,
    ) -> GetStadiumInfoToolResult:
        """stadium_id 또는 team_id 기준으로 정형 구장 정보를 조회합니다."""

        logger.info(
            "get_stadium_info tool started stadium_id=%s team_id=%s",
            tool_input.stadium_id,
            tool_input.team_id,
        )

        stadium_id = tool_input.stadium_id
        if stadium_id is None and tool_input.team_id is not None:
            stadium_id = await self._home_stadium_id_for_team(tool_input.team_id)

        if stadium_id is None:
            logger.info(
                "get_stadium_info tool completed found=false reason=no_stadium_id"
            )
            return GetStadiumInfoToolResult(
                found=False,
                stadium=None,
                limitations=["stadium_not_found"],
            )

        stadium = await self._stadium_by_id(stadium_id)
        if stadium is None:
            logger.info(
                "get_stadium_info tool completed stadium_id=%s found=false",
                stadium_id,
            )
            return GetStadiumInfoToolResult(
                found=False,
                stadium=None,
                limitations=["stadium_not_found"],
            )

        home_team_ids = await self._home_team_ids_for_stadium(stadium.id)

        logger.info(
            "get_stadium_info tool completed stadium_id=%s found=true",
            stadium.id,
        )
        return GetStadiumInfoToolResult(
            found=True,
            stadium=StadiumInfoItem(
                stadium_id=stadium.id,
                name_ko=stadium.name_ko,
                short_name=stadium.short_name,
                aliases=list(stadium.aliases or []),
                city=stadium.city,
                region=stadium.region,
                address=stadium.address,
                latitude=(
                    float(stadium.latitude) if stadium.latitude is not None else None
                ),
                longitude=(
                    float(stadium.longitude) if stadium.longitude is not None else None
                ),
                is_dome=stadium.is_dome,
                home_team_id=stadium.home_team_id,
                home_team_ids=home_team_ids,
                official_url=stadium.official_url,
                source_url=stadium.source_url,
                as_of=stadium.as_of,
                metadata=dict(stadium.metadata_ or {}),
            ),
            limitations=[],
        )

    async def _home_stadium_id_for_team(self, team_id: str) -> str | None:
        statement = select(KboTeamModel.home_stadium_id).where(
            KboTeamModel.id == team_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def _stadium_by_id(self, stadium_id: str) -> KboStadiumModel | None:
        statement = select(KboStadiumModel).where(KboStadiumModel.id == stadium_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def _home_team_ids_for_stadium(self, stadium_id: str) -> list[str]:
        statement = (
            select(KboTeamModel.id)
            .where(KboTeamModel.home_stadium_id == stadium_id)
            .order_by(KboTeamModel.id.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
