from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_create_conversation_service,
    get_current_auth_user,
    get_list_conversation_messages_service,
    get_list_conversations_service,
)
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.conversation.controller.schemas import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageListResponse,
    MessageResponse,
)
from app.domains.conversation.domain.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
)
from app.domains.conversation.service.dto import (
    CreateConversationCommand,
    ListConversationMessagesQuery,
    ListConversationsQuery,
)
from app.domains.conversation.service.services import (
    CreateConversationService,
    ListConversationMessagesService,
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
ListConversationMessagesServiceDependency = Annotated[
    ListConversationMessagesService,
    Depends(get_list_conversation_messages_service),
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


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conversation_messages(
    conversation_id: UUID,
    service: ListConversationMessagesServiceDependency,
    current_user: CurrentUserDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageListResponse:
    """로그인 사용자의 대화방 메시지 목록을 조회합니다."""

    query = ListConversationMessagesQuery(
        conversation_id=conversation_id,
        user_profile_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    try:
        results = await service.execute(query)
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation_not_found",
        )
    except ConversationAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="conversation_access_denied",
        )

    return MessageListResponse(
        messages=[
            MessageResponse.model_validate(result)
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
