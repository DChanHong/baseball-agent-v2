from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.conversation.domain.enums import ConversationStatus


class CreateConversationRequest(BaseModel):
    """대화방 생성 HTTP 요청 Schema입니다."""

    guest_id: UUID
    title: str | None = Field(default=None, max_length=200)
    agent_type: str = Field(
        default="baseball_general",
        min_length=1,
        max_length=50,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    """대화방 HTTP 응답 Schema입니다."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    guest_id: UUID | None
    title: str | None
    status: ConversationStatus
    agent_type: str
    summary: str | None
    metadata: dict[str, Any]
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
