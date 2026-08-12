from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.conversation.domain.entities import Conversation, Message
from app.domains.conversation.infrastructure.mappers import (
    ConversationMapper,
    MessageMapper,
)
from app.domains.conversation.infrastructure.models import (
    ChatConversationModel,
    ChatMessageModel,
)


class SqlAlchemyConversationRepository:
    """PostgreSQL을 사용하는 대화방 Repository 구현체입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> Conversation:
        """새 대화방을 현재 트랜잭션에 추가합니다."""

        model = ConversationMapper.to_model(conversation)

        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        return ConversationMapper.to_domain(model)

    async def find_by_id(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """삭제되지 않은 대화방을 ID로 조회합니다."""

        statement = select(ChatConversationModel).where(
            ChatConversationModel.id == conversation_id,
            ChatConversationModel.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ConversationMapper.to_domain(model)

    async def list_by_guest_id(
        self,
        guest_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """guest_id에 속한 대화방을 최근 메시지 순으로 조회합니다."""

        statement = (
            select(ChatConversationModel)
            .where(
                ChatConversationModel.guest_id == guest_id,
                ChatConversationModel.deleted_at.is_(None),
            )
            .order_by(
                ChatConversationModel.last_message_at.desc().nullslast(),
                ChatConversationModel.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        models = result.scalars().all()

        return [ConversationMapper.to_domain(model) for model in models]

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """user_id에 속한 대화방을 최근 메시지 순으로 조회합니다."""

        statement = (
            select(ChatConversationModel)
            .where(
                ChatConversationModel.user_id == user_id,
                ChatConversationModel.deleted_at.is_(None),
            )
            .order_by(
                ChatConversationModel.last_message_at.desc().nullslast(),
                ChatConversationModel.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        models = result.scalars().all()

        return [ConversationMapper.to_domain(model) for model in models]

    async def list_by_user_profile_id(
        self,
        user_profile_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """user_profile_id에 속한 대화방을 최근 메시지 순으로 조회합니다."""

        statement = (
            select(ChatConversationModel)
            .where(
                ChatConversationModel.user_profile_id == user_profile_id,
                ChatConversationModel.deleted_at.is_(None),
            )
            .order_by(
                ChatConversationModel.last_message_at.desc().nullslast(),
                ChatConversationModel.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        models = result.scalars().all()

        return [ConversationMapper.to_domain(model) for model in models]

    async def save(
        self,
        conversation: Conversation,
    ) -> Conversation:
        """기존 대화방의 변경 가능한 필드를 저장합니다."""

        statement = select(ChatConversationModel).where(
            ChatConversationModel.id == conversation.id,
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError("저장할 대화방을 찾을 수 없습니다.")

        model.user_id = conversation.user_id
        model.user_profile_id = conversation.user_profile_id
        model.guest_id = conversation.guest_id
        model.title = conversation.title
        model.status = conversation.status.value
        model.agent_type = conversation.agent_type
        model.summary = conversation.summary
        model.extra_metadata = dict(conversation.metadata)
        model.last_message_at = conversation.last_message_at
        model.deleted_at = conversation.deleted_at

        await self._session.flush()
        await self._session.refresh(model)

        return ConversationMapper.to_domain(model)


class SqlAlchemyMessageRepository:
    """PostgreSQL을 사용하는 메시지 Repository 구현체입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> Message:
        """새 메시지를 현재 트랜잭션에 추가합니다."""

        model = MessageMapper.to_model(message)

        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        return MessageMapper.to_domain(model)

    async def find_by_id(
        self,
        message_id: UUID,
    ) -> Message | None:
        """메시지를 ID로 조회합니다."""

        statement = select(ChatMessageModel).where(
            ChatMessageModel.id == message_id,
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return MessageMapper.to_domain(model)

    async def save(
        self,
        message: Message,
    ) -> Message:
        """기존 메시지의 변경 가능한 필드를 저장합니다."""

        statement = select(ChatMessageModel).where(
            ChatMessageModel.id == message.id,
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError("저장할 메시지를 찾을 수 없습니다.")

        model.content = message.content
        model.content_type = message.content_type.value
        model.status = message.status.value
        model.parent_message_id = message.parent_message_id
        model.model_name = message.model_name
        model.prompt_tokens = message.prompt_tokens
        model.completion_tokens = message.completion_tokens
        model.total_tokens = message.total_tokens
        model.latency_ms = message.latency_ms
        model.error_code = message.error_code
        model.extra_metadata = dict(message.metadata)
        model.deleted_at = message.deleted_at

        await self._session.flush()
        await self._session.refresh(model)

        return MessageMapper.to_domain(model)

    async def list_by_conversation_id(
        self,
        conversation_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """대화방 메시지를 sequence_no 오름차순으로 조회합니다."""

        statement = (
            select(ChatMessageModel)
            .where(
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.deleted_at.is_(None),
            )
            .order_by(ChatMessageModel.sequence_no.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        models = result.scalars().all()

        return [MessageMapper.to_domain(model) for model in models]

    async def get_next_sequence_no(
        self,
        conversation_id: UUID,
    ) -> int:
        """
        대화방 행을 잠근 뒤 다음 메시지 순번을 계산합니다.

        같은 대화방에 여러 요청이 동시에 들어와도
        sequence_no가 중복되지 않도록 직렬화합니다.
        """

        lock_statement = (
            select(ChatConversationModel.id)
            .where(ChatConversationModel.id == conversation_id)
            .with_for_update()
        )

        lock_result = await self._session.execute(lock_statement)

        if lock_result.scalar_one_or_none() is None:
            raise ValueError("메시지를 추가할 대화방을 찾을 수 없습니다.")

        sequence_statement = select(
            func.coalesce(
                func.max(ChatMessageModel.sequence_no),
                0,
            )
            + 1
        ).where(
            ChatMessageModel.conversation_id == conversation_id,
            ChatMessageModel.deleted_at.is_(None),
        )

        sequence_result = await self._session.execute(sequence_statement)

        return sequence_result.scalar_one()
