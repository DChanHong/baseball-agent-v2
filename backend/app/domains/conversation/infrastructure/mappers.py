from app.domains.conversation.domain.entities import Conversation, Message
from app.domains.conversation.domain.enums import (
    ConversationStatus,
    MessageContentType,
    MessageRole,
    MessageStatus,
)
from app.domains.conversation.infrastructure.models import (
    ChatConversationModel,
    ChatMessageModel,
)


class ConversationMapper:
    """대화방 ORM Model과 Domain Entity 사이를 변환합니다."""

    @staticmethod
    def to_domain(model: ChatConversationModel) -> Conversation:
        """SQLAlchemy ORM Model을 순수 Domain Entity로 변환합니다."""

        return Conversation(
            id=model.id,
            user_id=model.user_id,
            guest_id=model.guest_id,
            title=model.title,
            status=ConversationStatus(model.status),
            agent_type=model.agent_type,
            summary=model.summary,
            metadata=dict(model.extra_metadata),
            last_message_at=model.last_message_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: Conversation) -> ChatConversationModel:
        """순수 Domain Entity를 SQLAlchemy ORM Model로 변환합니다."""

        return ChatConversationModel(
            id=entity.id,
            user_id=entity.user_id,
            guest_id=entity.guest_id,
            title=entity.title,
            status=entity.status.value,
            agent_type=entity.agent_type,
            summary=entity.summary,
            extra_metadata=dict(entity.metadata),
            last_message_at=entity.last_message_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )


class MessageMapper:
    """메시지 ORM Model과 Domain Entity 사이를 변환합니다."""

    @staticmethod
    def to_domain(model: ChatMessageModel) -> Message:
        """SQLAlchemy ORM Model을 순수 Domain Entity로 변환합니다."""

        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            user_id=model.user_id,
            role=MessageRole(model.role),
            content=model.content,
            content_type=MessageContentType(model.content_type),
            sequence_no=model.sequence_no,
            status=MessageStatus(model.status),
            parent_message_id=model.parent_message_id,
            model_name=model.model_name,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            total_tokens=model.total_tokens,
            latency_ms=model.latency_ms,
            error_code=model.error_code,
            metadata=dict(model.extra_metadata),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Message) -> ChatMessageModel:
        """순수 Domain Entity를 SQLAlchemy ORM Model로 변환합니다."""

        return ChatMessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            user_id=entity.user_id,
            role=entity.role.value,
            content=entity.content,
            content_type=entity.content_type.value,
            sequence_no=entity.sequence_no,
            status=entity.status.value,
            parent_message_id=entity.parent_message_id,
            model_name=entity.model_name,
            prompt_tokens=entity.prompt_tokens,
            completion_tokens=entity.completion_tokens,
            total_tokens=entity.total_tokens,
            latency_ms=entity.latency_ms,
            error_code=entity.error_code,
            extra_metadata=dict(entity.metadata),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
