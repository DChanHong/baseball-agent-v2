from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_create_conversation_service,
    get_current_auth_user,
    get_list_conversations_service,
)
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.conversation.controller.schemas import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
)
from app.domains.conversation.service.dto import (
    CreateConversationCommand,
    ListConversationsQuery,
)
from app.domains.conversation.service.services import (
    CreateConversationService,
    ListConversationsService,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)

CreateConversationServiceDependency = Annotated[
    CreateConversationService,
    Depends(get_create_conversation_service),
]
ListConversationsServiceDependency = Annotated[
    ListConversationsService,
    Depends(get_list_conversations_service),
]
CurrentUserDependency = Annotated[
    CurrentUserDto,
    Depends(get_current_auth_user),
]


@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conversations(
    service: ListConversationsServiceDependency,
    current_user: CurrentUserDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationListResponse:
    """로그인 사용자의 대화방 목록을 최근 순으로 조회합니다."""

    query = ListConversationsQuery(
        user_profile_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    results = await service.execute(query)

    return ConversationListResponse(
        conversations=[
            ConversationResponse.model_validate(result)
            for result in results
        ],
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
async def create_conversation(
    request: CreateConversationRequest,
    service: CreateConversationServiceDependency,
    current_user: CurrentUserDependency,
) -> ConversationResponse:
    """로그인 사용자의 새 대화방을 생성합니다."""

    command = CreateConversationCommand(
        user_profile_id=current_user.id,
        title=request.title,
        agent_type=request.agent_type,
        metadata=dict(request.metadata),
    )

    result = await service.execute(command)

    return ConversationResponse.model_validate(result)
