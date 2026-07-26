from enum import StrEnum


class ConversationStatus(StrEnum):
    """대화방의 현재 상태입니다."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(StrEnum):
    """메시지를 생성한 주체 또는 역할입니다."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageContentType(StrEnum):
    """메시지 콘텐츠의 저장 형식입니다."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    IMAGE = "image"
    FILE = "file"


class MessageStatus(StrEnum):
    """메시지 생성 및 처리 상태입니다."""

    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
