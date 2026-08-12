from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_stream_service, get_current_auth_user
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.chat.controller.schemas import ChatStreamRequest
from app.domains.chat.service.services import ChatStreamService

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

ChatStreamServiceDependency = Annotated[
    ChatStreamService,
    Depends(get_chat_stream_service),
]
CurrentUserDependency = Annotated[
    CurrentUserDto,
    Depends(get_current_auth_user),
]


@router.post("")
async def stream_chat(
    request: ChatStreamRequest,
    service: ChatStreamServiceDependency,
    current_user: CurrentUserDependency,
) -> StreamingResponse:
    """Run one chat turn and stream conversation/tool/assistant events."""

    return StreamingResponse(
        service.stream(request, current_user=current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
