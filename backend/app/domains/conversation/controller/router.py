from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_create_conversation_service, get_current_auth_user
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.conversation.controller.schemas import (
    ConversationResponse,
    CreateConversationRequest,
)
from app.domains.conversation.service.dto import (
    CreateConversationCommand,
)
from app.domains.conversation.service.services import (
    CreateConversationService,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)

CreateConversationServiceDependency = Annotated[
    CreateConversationService,
    Depends(get_create_conversation_service),
]
CurrentUserDependency = Annotated[
    CurrentUserDto,
    Depends(get_current_auth_user),
]


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
