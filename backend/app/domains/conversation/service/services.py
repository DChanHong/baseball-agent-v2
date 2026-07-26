from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.conversation.domain.entities import Conversation
from app.domains.conversation.domain.enums import ConversationStatus
from app.domains.conversation.domain.repositories import (
    ConversationRepository,
)
from app.domains.conversation.service.dto import (
    ConversationResultDto,
    CreateConversationCommand,
)


class CreateConversationService:
    """비로그인 사용자의 새 대화방을 생성하는 유스케이스입니다."""

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
            guest_id=command.guest_id,
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
