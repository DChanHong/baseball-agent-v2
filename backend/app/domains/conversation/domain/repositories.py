from typing import Protocol
from uuid import UUID

from app.domains.conversation.domain.entities import Conversation, Message


class ConversationRepository(Protocol):
    """
    대화방 저장소의 도메인 인터페이스입니다.

    Domain 계층은 실제 저장 기술이 PostgreSQL인지,
    SQLAlchemy인지 알지 못합니다.
    """

    async def add(self, conversation: Conversation) -> Conversation:
        """새 대화방을 저장하고 저장된 Entity를 반환합니다."""

        ...

    async def find_by_id(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """ID로 삭제되지 않은 대화방을 조회합니다."""

        ...

    async def list_by_guest_id(
        self,
        guest_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """비로그인 사용자의 대화방 목록을 최근 순으로 조회합니다."""

        ...

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """로그인 사용자의 대화방 목록을 최근 순으로 조회합니다."""

        ...

    async def list_by_user_profile_id(
        self,
        user_profile_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """로그인 사용자의 프로필 ID에 속한 대화방 목록을 최근 순으로 조회합니다."""

        ...

    async def save(self, conversation: Conversation) -> Conversation:
        """변경된 대화방 상태를 저장합니다."""

        ...


class MessageRepository(Protocol):
    """
    메시지 저장소의 도메인 인터페이스입니다.

    SQLAlchemy Session이나 SQL 문장은 이 인터페이스에 노출하지 않습니다.
    """

    async def add(self, message: Message) -> Message:
        """새 메시지를 저장하고 저장된 Entity를 반환합니다."""

        ...

    async def find_by_id(
        self,
        message_id: UUID,
    ) -> Message | None:
        """메시지 ID로 단일 메시지를 조회합니다."""

        ...

    async def save(self, message: Message) -> Message:
        """변경된 메시지 상태를 저장합니다."""

        ...

    async def list_by_conversation_id(
        self,
        conversation_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """대화방 메시지를 sequence_no 오름차순으로 조회합니다."""

        ...

    async def get_next_sequence_no(
        self,
        conversation_id: UUID,
    ) -> int:
        """대화방에 추가할 다음 메시지 순번을 계산합니다."""

        ...
