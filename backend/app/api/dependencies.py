from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.domains.baseball.infrastructure.repositories import (
    SqlAlchemyKboGameRepository,
)
from app.domains.baseball.service.services import (
    ListKboGamesService,
)
from app.domains.conversation.infrastructure.repositories import (
    SqlAlchemyConversationRepository,
)
from app.domains.conversation.service.services import (
    CreateConversationService,
)

# FastAPI가 요청마다 생성한 DB Session을 주입하는 공통 타입입니다.
DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


def get_create_conversation_service(
    session: DatabaseSession,
) -> CreateConversationService:
    """대화방 생성 유스케이스에 필요한 의존성을 조립합니다."""

    repository = SqlAlchemyConversationRepository(session)

    return CreateConversationService(
        repository=repository,
        session=session,
    )


def get_list_kbo_games_service(
    session: DatabaseSession,
) -> ListKboGamesService:
    """KBO 경기 조회 유스케이스에 필요한 의존성을 조립합니다."""

    repository = SqlAlchemyKboGameRepository(session)

    return ListKboGamesService(repository=repository)
