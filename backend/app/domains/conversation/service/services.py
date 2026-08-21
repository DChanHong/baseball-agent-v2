from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.conversation.domain.entities import Conversation
from app.domains.conversation.domain.enums import ConversationStatus
from app.domains.conversation.domain.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
)
from app.domains.conversation.domain.repositories import (
    ConversationRepository,
    MessageRepository,
)
from app.domains.conversation.service.dto import (
    ConversationResultDto,
    CreateConversationCommand,
    ListConversationMessagesQuery,
    ListConversationsQuery,
    MessageResultDto,
)


class CreateConversationService:
    """로그인 사용자의 새 대화방을 생성하는 유스케이스입니다."""

    def __init__(
        self,
        repository: ConversationRepository,
        session: AsyncSession,
    ) -> None:
        self._repository = repository
        self._session = session

    async def execute(
        self,
        command: CreateConversationCommand,
    ) -> ConversationResultDto:
        """대화방을 생성하고 트랜잭션을 확정합니다."""

        now = datetime.now(UTC)

        conversation = Conversation(
            id=uuid4(),
            user_id=None,
            user_profile_id=command.user_profile_id,
            guest_id=None,
            title=command.title,
            status=ConversationStatus.ACTIVE,
            agent_type=command.agent_type,
            summary=None,
            metadata=dict(command.metadata),
            last_message_at=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        try:
            saved_conversation = await self._repository.add(conversation)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        return ConversationResultDto.from_entity(saved_conversation)


class ListConversationMessagesService:
    """로그인 사용자의 대화방 메시지 목록을 조회하는 유스케이스입니다."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository

    async def execute(
        self,
        query: ListConversationMessagesQuery,
    ) -> list[MessageResultDto]:
        """대화방 소유권을 확인한 후 메시지 목록을 반환합니다."""

        conversation = await self._conversation_repository.find_by_id(
            query.conversation_id,
        )

        if conversation is None:
            raise ConversationNotFoundError(str(query.conversation_id))

        if conversation.user_profile_id != query.user_profile_id:
            raise ConversationAccessDeniedError(str(query.conversation_id))

        messages = await self._message_repository.list_by_conversation_id(
            query.conversation_id,
            limit=query.limit,
            offset=query.offset,
        )

        return [
            MessageResultDto.from_entity(message)
            for message in messages
            if message.role.value in ("user", "assistant")
        ]


class ListConversationsService:
    """로그인 사용자의 대화방 목록을 조회하는 유스케이스입니다."""

    def __init__(
        self,
        repository: ConversationRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        query: ListConversationsQuery,
    ) -> list[ConversationResultDto]:
        """대화방 목록을 최근 대화 순으로 반환합니다."""

        conversations = await self._repository.list_by_user_profile_id(
            query.user_profile_id,
            limit=query.limit,
            offset=query.offset,
        )

        return [
            ConversationResultDto.from_entity(conversation)
            for conversation in conversations
        ]
