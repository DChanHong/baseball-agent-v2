from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_list_kbo_games_service
from app.domains.baseball.controller.schemas import KboGameResponse
from app.domains.baseball.service.dto import ListKboGamesQuery
from app.domains.baseball.service.services import ListKboGamesService

router = APIRouter(
    prefix="/games",
    tags=["Games"],
)

ListKboGamesServiceDependency = Annotated[
    ListKboGamesService,
    Depends(get_list_kbo_games_service),
]


@router.get(
    "",
    response_model=list[KboGameResponse],
)
async def list_kbo_games(
    service: ListKboGamesServiceDependency,
    team_id: Annotated[str | None, Query(min_length=1)] = None,
    date_: Annotated[date | None, Query(alias="date")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[KboGameResponse]:
    """조건에 맞는 KBO 경기 일정을 조회합니다."""

    try:
        query = ListKboGamesQuery(
            team_id=team_id,
            date=date_,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    results = await service.execute(query)

    return [KboGameResponse.model_validate(result) for result in results]
