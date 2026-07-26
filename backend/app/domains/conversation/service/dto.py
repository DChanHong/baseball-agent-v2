from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from app.domains.conversation.domain.entities import Conversation
from app.domains.conversation.domain.enums import ConversationStatus


@dataclass(frozen=True, slots=True)
class CreateConversationCommand:
    """
    대화방 생성 Service에 전달하는 입력 DTO입니다.

    현재는 로그인 전 단계이므로 guest_id를 필수로 받습니다.
    """

    guest_id: UUID
    title: str | None = None
    agent_type: str = "baseball_general"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Service에 전달할 기본 입력값을 검증합니다."""

        if self.title is not None and len(self.title) > 200:
            raise ValueError("대화방 제목은 200자를 초과할 수 없습니다.")

        if not self.agent_type.strip():
            raise ValueError("agent_type은 빈 문자열일 수 없습니다.")

        if len(self.agent_type) > 50:
            raise ValueError("agent_type은 50자를 초과할 수 없습니다.")


@dataclass(frozen=True, slots=True)
class ConversationResultDto:
    """Service가 Controller에 반환하는 대화방 결과 DTO입니다."""

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

    @classmethod
    def from_entity(
        cls,
        conversation: Conversation,
    ) -> Self:
        """Domain Entity를 Service 결과 DTO로 변환합니다."""

        return cls(
            id=conversation.id,
            user_id=conversation.user_id,
            guest_id=conversation.guest_id,
            title=conversation.title,
            status=conversation.status,
            agent_type=conversation.agent_type,
            summary=conversation.summary,
            metadata=dict(conversation.metadata),
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            deleted_at=conversation.deleted_at,
        )
