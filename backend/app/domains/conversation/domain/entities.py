from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domains.conversation.domain.enums import (
    ConversationStatus,
    MessageContentType,
    MessageRole,
    MessageStatus,
)


#  frozen=True는 생성 후 필드가 임의로 변경되는 것을 막습니다.
#  slots=True: 허용되지 않은 속성이 실수로 추가되는 것을 방지합니다.
@dataclass(frozen=True, slots=True)
class Conversation:
    """
    채팅 대화방을 나타내는 순수 도메인 객체입니다.

    FastAPI, SQLAlchemy, Supabase에 의존하지 않으며
    애플리케이션 내부의 대화방 상태를 표현합니다.
    """

    id: UUID
    user_id: UUID | None
    user_profile_id: UUID | None
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

    def __post_init__(self) -> None:
        """대화방 상태와 삭제 시각의 일관성을 검사합니다."""
        if self.status is ConversationStatus.DELETED and self.deleted_at is None:
            raise ValueError("삭제된 대화방에는 deleted_at이 필요합니다.")
        if (
            self.status is not ConversationStatus.DELETED
            and self.deleted_at is not None
        ):
            raise ValueError("삭제되지 않은 대화방에는 deleted_at이 필요하지 않습니다.")


@dataclass(frozen=True, slots=True)
class Message:
    """
    대화방 안의 메시지를 나타내는 순수 도메인 객체입니다.

    메시지 순서, 처리 상태, 토큰 사용량과 같은
    애플리케이션 내부 데이터를 표현합니다.
    """

    id: UUID
    conversation_id: UUID
    user_id: UUID | None
    user_profile_id: UUID | None
    role: MessageRole
    content: str
    content_type: MessageContentType
    sequence_no: int
    status: MessageStatus
    parent_message_id: UUID | None
    model_name: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None
    error_code: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    def __post_init__(self) -> None:
        """메시지 순서와 성능 측정값이 올바른지 검사합니다."""

        if self.sequence_no <= 0:
            raise ValueError("sequence_no는 1 이상이어야 합니다.")

        nemeric_values = {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
        }

        for name, value in nemeric_values.items():
            if value is not None and value < 0:
                raise ValueError(f"{name}는 0 이상이어야 합니다.")

        if (
            self.prompt_tokens is not None
            and self.completion_tokens is not None
            and self.total_tokens is not None
            and self.total_tokens != self.prompt_tokens + self.completion_tokens
        ):
            raise ValueError(
                "total_tokens는 prompt_tokens와 completion_tokens의 합이어야 합니다."
            )
