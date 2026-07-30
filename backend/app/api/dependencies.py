from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tool_executor import AgentToolExecutor
from app.core.database import get_db_session
from app.core.llm import get_openai_client
from app.domains.baseball.infrastructure.repositories import (
    SqlAlchemyKboGameRepository,
)
from app.domains.baseball.service.services import (
    ListKboGamesService,
)
from app.domains.baseball.tool.find_kbo_game.handler import FindKboGameToolHandler
from app.domains.baseball.tool.search_stadium_guide.handler import (
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.retriever import (
    PgVectorStadiumGuideRetriever,
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


def get_find_kbo_game_tool_handler(
    session: DatabaseSession,
) -> FindKboGameToolHandler:
    """KBO 경기 조회 Tool 실행에 필요한 의존성을 조립합니다."""

    repository = SqlAlchemyKboGameRepository(session)
    service = ListKboGamesService(repository=repository)

    return FindKboGameToolHandler(service=service)


def get_search_stadium_guide_tool_handler(
    session: DatabaseSession,
) -> SearchStadiumGuideToolHandler:
    """구장 안내 RAG Tool 실행에 필요한 의존성을 조립합니다."""

    return SearchStadiumGuideToolHandler(
        openai_client=get_openai_client(),
        retriever=PgVectorStadiumGuideRetriever(session),
    )


def get_agent_tool_executor(
    session: DatabaseSession,
) -> AgentToolExecutor:
    """Agent routing 결과를 실제 Tool handler로 실행하는 의존성을 조립합니다."""

    return AgentToolExecutor(
        find_kbo_game_handler=get_find_kbo_game_tool_handler(session),
        search_stadium_guide_handler=get_search_stadium_guide_tool_handler(session),
    )
