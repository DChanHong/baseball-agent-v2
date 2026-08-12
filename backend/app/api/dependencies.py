from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.routing_service import ToolRoutingService
from app.agent.tool_executor import AgentToolExecutor
from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.llm import get_openai_client
from app.domains.auth.domain.exceptions import (
    AuthConfigurationError,
    UnauthenticatedError,
)
from app.domains.auth.infrastructure.repositories import (
    SqlAlchemyUserProfileRepository,
)
from app.domains.auth.infrastructure.supabase_auth_client import SupabaseAuthClient
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.auth.service.services import AuthRedirectService, AuthSessionService
from app.domains.baseball.infrastructure.repositories import (
    SqlAlchemyKboGameRepository,
)
from app.domains.baseball.service.services import (
    ListKboGamesService,
)
from app.domains.baseball.tool.find_kbo_game.handler import FindKboGameToolHandler
from app.domains.baseball.tool.get_stadium_info.handler import (
    GetStadiumInfoToolHandler,
)
from app.domains.baseball.tool.get_weather_context.handler import (
    GetWeatherContextToolHandler,
)
from app.domains.baseball.tool.get_weather_context.kma_client import KmaClient
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.retriever import (
    PgVectorBaseballKnowledgeRetriever,
)
from app.domains.baseball.tool.search_stadium_guide.handler import (
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.retriever import (
    PgVectorStadiumGuideRetriever,
)
from app.domains.baseball.tool.search_ticketing_guide.handler import (
    SearchTicketingGuideToolHandler,
)
from app.domains.chat.service.services import ChatStreamService
from app.domains.conversation.infrastructure.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
)
from app.domains.conversation.service.services import (
    CreateConversationService,
    ListConversationsService,
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


def get_list_conversations_service(
    session: DatabaseSession,
) -> ListConversationsService:
    """대화방 목록 조회 유스케이스에 필요한 의존성을 조립합니다."""

    repository = SqlAlchemyConversationRepository(session)

    return ListConversationsService(repository=repository)


def get_auth_redirect_service() -> AuthRedirectService:
    """Auth OAuth redirect flow에 필요한 의존성을 조립합니다."""

    return AuthRedirectService(settings=get_settings())


def get_auth_session_service(
    session: DatabaseSession,
) -> AuthSessionService:
    """Auth session 처리에 필요한 의존성을 조립합니다."""

    return AuthSessionService(
        supabase_auth_client=SupabaseAuthClient(settings=get_settings()),
        user_profile_repository=SqlAlchemyUserProfileRepository(session),
        session=session,
    )


async def get_current_auth_user(
    request: Request,
    service: Annotated[AuthSessionService, Depends(get_auth_session_service)],
) -> CurrentUserDto:
    """Resolve the authenticated application profile from the access cookie."""

    settings = get_settings()
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        )

    try:
        return await service.get_current_user(access_token)
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_configured",
        ) from exc
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        ) from exc


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


def get_search_ticketing_guide_tool_handler(
    session: DatabaseSession,
) -> SearchTicketingGuideToolHandler:
    """예매 안내 RAG Tool 실행에 필요한 의존성을 조립합니다."""

    return SearchTicketingGuideToolHandler(
        openai_client=get_openai_client(),
        retriever=PgVectorStadiumGuideRetriever(session),
    )


def get_search_baseball_knowledge_tool_handler(
    session: DatabaseSession,
) -> SearchBaseballKnowledgeToolHandler:
    """야구 지식 RAG Tool 실행에 필요한 의존성을 조립합니다."""

    return SearchBaseballKnowledgeToolHandler(
        openai_client=get_openai_client(),
        retriever=PgVectorBaseballKnowledgeRetriever(session),
    )


def get_stadium_info_tool_handler(
    session: DatabaseSession,
) -> GetStadiumInfoToolHandler:
    """정형 구장 정보 Tool 실행에 필요한 의존성을 조립합니다."""

    return GetStadiumInfoToolHandler(session=session)


def get_weather_context_tool_handler() -> GetWeatherContextToolHandler:
    """구장 기준 날씨 context Tool 실행에 필요한 의존성을 조립합니다."""

    settings = get_settings()
    return GetWeatherContextToolHandler(
        kma_client=KmaClient(
            endpoint=settings.kma_api_endpoint,
            service_key=settings.kma_service_key,
        )
    )


def get_agent_tool_executor(
    session: DatabaseSession,
) -> AgentToolExecutor:
    """Agent routing 결과를 실제 Tool handler로 실행하는 의존성을 조립합니다."""

    return AgentToolExecutor(
        find_kbo_game_handler=get_find_kbo_game_tool_handler(session),
        get_stadium_info_handler=get_stadium_info_tool_handler(session),
        search_stadium_guide_handler=get_search_stadium_guide_tool_handler(session),
        search_ticketing_guide_handler=get_search_ticketing_guide_tool_handler(
            session
        ),
        search_baseball_knowledge_handler=get_search_baseball_knowledge_tool_handler(
            session
        ),
        get_weather_context_handler=get_weather_context_tool_handler(),
    )


def get_chat_stream_service(
    session: DatabaseSession,
) -> ChatStreamService:
    """Streaming chat endpoint에 필요한 의존성을 조립합니다."""

    return ChatStreamService(
        conversation_repository=SqlAlchemyConversationRepository(session),
        message_repository=SqlAlchemyMessageRepository(session),
        tool_routing_service=ToolRoutingService(),
        tool_executor=get_agent_tool_executor(session),
        session=session,
    )
