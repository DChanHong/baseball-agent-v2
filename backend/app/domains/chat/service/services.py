from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import BaseballAgentGraph
from app.agent.routing_service import ToolRoutingService
from app.agent.state import (
    AgentConversationContext,
    BaseballAgentInput,
    BaseballAgentOutput,
)
from app.agent.tool_executor import AgentToolExecutor
from app.core.config import get_settings
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.chat.controller.schemas import (
    AssistantCompletedEvent,
    AssistantDeltaEvent,
    ChatStreamMessage,
    ChatStreamRequest,
    ConversationCreatedEvent,
    ConversationUpdatedEvent,
    ConversationUpdatedSummary,
    DoneEvent,
    MessageCreatedEvent,
    StreamError,
    StreamFailedEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
    ToolStartedEvent,
)
from app.domains.chat.service.sse import encode_sse_event
from app.domains.conversation.domain.entities import Conversation, Message
from app.domains.conversation.domain.enums import (
    ConversationStatus,
    MessageContentType,
    MessageRole,
    MessageStatus,
)
from app.domains.conversation.infrastructure.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
)

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class ChatStreamService:
    """Runs a chat turn and emits stable SSE events for the frontend."""

    def __init__(
        self,
        *,
        conversation_repository: SqlAlchemyConversationRepository,
        message_repository: SqlAlchemyMessageRepository,
        agent_graph: BaseballAgentGraph | None = None,
        tool_routing_service: ToolRoutingService | None = None,
        tool_executor: AgentToolExecutor | None = None,
        session: AsyncSession,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository
        if agent_graph is None:
            if tool_routing_service is None or tool_executor is None:
                raise ValueError(
                    "agent_graph or both tool_routing_service and tool_executor are required"
                )
            agent_graph = BaseballAgentGraph(
                tool_routing_service=tool_routing_service,
                tool_executor=tool_executor,
            )
        self._agent_graph = agent_graph
        self._session = session

    async def stream(
        self,
        request: ChatStreamRequest,
        *,
        current_user: CurrentUserDto,
    ) -> AsyncIterator[str]:
        """Execute one chat request and yield encoded SSE event chunks."""

        try:
            async for event in self._stream_inner(
                request,
                current_user=current_user,
            ):
                yield event
        except Exception:
            logger.exception("chat stream failed")
            await self._session.rollback()
            yield encode_sse_event(
                "stream.failed",
                StreamFailedEvent(
                    error=StreamError(
                        code="chat_stream_failed",
                        message="채팅 응답을 생성하는 중 문제가 발생했습니다.",
                    )
                ),
            )

    async def _stream_inner(
        self,
        request: ChatStreamRequest,
        *,
        current_user: CurrentUserDto,
    ) -> AsyncIterator[str]:
        now = datetime.now(UTC)
        conversation, created = await self._get_or_create_conversation(
            user_profile_id=current_user.id,
            conversation_id=request.conversation_id,
            now=now,
            title=_build_title(request.message),
        )
        await self._session.commit()

        yield encode_sse_event(
            "conversation.created",
            ConversationCreatedEvent(
                conversation_id=conversation.id,
                created=created,
            ),
        )

        user_message = await self._create_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
            status=MessageStatus.COMPLETED,
            parent_message_id=None,
            metadata={},
            user_profile_id=current_user.id,
        )
        await self._session.commit()

        yield encode_sse_event(
            "message.created",
            MessageCreatedEvent(message=_to_stream_message(user_message)),
        )

        assistant_message = await self._create_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="",
            status=MessageStatus.STREAMING,
            parent_message_id=user_message.id,
            metadata={},
            user_profile_id=current_user.id,
        )
        await self._session.commit()

        yield encode_sse_event(
            "message.created",
            MessageCreatedEvent(message=_to_stream_message(assistant_message)),
        )

        started_at = perf_counter()
        graph_output: BaseballAgentOutput | None = None
        async for graph_event in self._agent_graph.astream(
            BaseballAgentInput(
                conversation_id=conversation.id,
                user_profile_id=current_user.id,
                user_message=request.message,
                today=datetime.now(KST).date(),
                timezone="Asia/Seoul",
                favorite_team_id=current_user.favorite_team,
                context=_load_agent_context(conversation.metadata),
            )
        ):
            if graph_event.kind == "tool.started":
                if graph_event.tool_call_id is None or graph_event.tool_name is None:
                    raise ValueError("tool.started graph event is missing tool identity")
                tool_input = graph_event.tool_input or {}
                yield encode_sse_event(
                    "tool.started",
                    ToolStartedEvent(
                        tool_call_id=graph_event.tool_call_id,
                        name=graph_event.tool_name,
                        status="running",
                        input=tool_input,
                    ),
                )
            elif graph_event.kind == "tool.failed":
                tool_payload = graph_event.tool_payload or {}
                tool_input = graph_event.tool_input or {}
                error = tool_payload.get("error")
                error_message = "도구 실행 중 문제가 발생했습니다."
                if isinstance(error, dict) and isinstance(error.get("message"), str):
                    error_message = error["message"]
                yield encode_sse_event(
                    "tool.failed",
                    ToolFailedEvent(
                        tool_call_id=graph_event.tool_call_id or "tool_unknown",
                        name=graph_event.tool_name or "find_kbo_game",
                        status="failed",
                        input=tool_input,
                        error=StreamError(
                            code="tool_execution_failed",
                            message=error_message,
                        ),
                    ),
                )
            elif graph_event.kind == "tool.completed":
                tool_payload = graph_event.tool_payload
                if tool_payload is None:
                    raise ValueError("tool.completed graph event is missing payload")
                result_payload = tool_payload.get("result")
                if not isinstance(result_payload, dict):
                    raise ValueError("tool.completed graph event is missing result")
                yield encode_sse_event(
                    "tool.completed",
                    ToolCompletedEvent(
                        tool_call_id=graph_event.tool_call_id or "tool_unknown",
                        name=graph_event.tool_name or "find_kbo_game",
                        status="completed",
                        input=graph_event.tool_input or {},
                        result=result_payload,
                    ),
                )
            elif graph_event.kind == "completed":
                if graph_event.output is None:
                    raise ValueError("completed graph event is missing output")
                graph_output = graph_event.output

        if graph_output is None:
            raise ValueError("agent graph did not produce a completed output")

        assistant_content = graph_output.answer
        tool_limitations = graph_output.tool_limitations

        for delta in _chunk_text(assistant_content):
            yield encode_sse_event(
                "assistant.delta",
                AssistantDeltaEvent(
                    message_id=assistant_message.id,
                    delta=delta,
                ),
            )

        completed_at = datetime.now(UTC)
        latency_ms = int((perf_counter() - started_at) * 1000)
        assistant_message = replace(
            assistant_message,
            content=assistant_content,
            status=MessageStatus.COMPLETED,
            latency_ms=latency_ms,
            metadata={
                "routing_decision": graph_output.routing_decision.model_dump(
                    mode="json"
                ),
                "tool_results": (
                    [graph_output.tool_payload]
                    if graph_output.tool_payload is not None
                    else []
                ),
                "limitations": tool_limitations,
                "agent_context": graph_output.context.model_dump(mode="json"),
            },
            updated_at=completed_at,
        )
        assistant_message = await self._message_repository.save(assistant_message)

        conversation_metadata = dict(conversation.metadata)
        conversation_metadata["agent_context"] = graph_output.context.model_dump(
            mode="json"
        )
        conversation = replace(
            conversation,
            title=conversation.title or _build_title(request.message),
            metadata=conversation_metadata,
            last_message_at=completed_at,
            updated_at=completed_at,
        )
        saved_conversation = await self._conversation_repository.save(conversation)
        await self._session.commit()

        yield encode_sse_event(
            "assistant.completed",
            AssistantCompletedEvent(
                message_id=assistant_message.id,
                content=assistant_content,
                sources=[],
                limitations=tool_limitations,
            ),
        )
        yield encode_sse_event(
            "conversation.updated",
            ConversationUpdatedEvent(
                conversation=ConversationUpdatedSummary(
                    id=saved_conversation.id,
                    title=saved_conversation.title,
                    last_message_at=saved_conversation.last_message_at,
                )
            ),
        )
        yield encode_sse_event(
            "done",
            DoneEvent(conversation_id=saved_conversation.id),
        )

    async def _get_or_create_conversation(
        self,
        *,
        user_profile_id: UUID,
        conversation_id: UUID | None,
        now: datetime,
        title: str,
    ) -> tuple[Conversation, bool]:
        if conversation_id is not None:
            conversation = await self._conversation_repository.find_by_id(
                conversation_id
            )
            if conversation is None:
                raise ValueError("conversation not found")
            if conversation.user_profile_id != user_profile_id:
                raise ValueError("conversation does not belong to user profile")
            return conversation, False

        conversation = Conversation(
            id=uuid4(),
            user_id=None,
            user_profile_id=user_profile_id,
            guest_id=None,
            title=title,
            status=ConversationStatus.ACTIVE,
            agent_type="baseball_general",
            summary=None,
            metadata={},
            last_message_at=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        return await self._conversation_repository.add(conversation), True

    async def _create_message(
        self,
        *,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        status: MessageStatus,
        parent_message_id: UUID | None,
        metadata: dict[str, object],
        user_profile_id: UUID,
    ) -> Message:
        now = datetime.now(UTC)
        sequence_no = await self._message_repository.get_next_sequence_no(
            conversation_id
        )
        message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            user_id=None,
            user_profile_id=user_profile_id,
            role=role,
            content=content,
            content_type=MessageContentType.MARKDOWN,
            sequence_no=sequence_no,
            status=status,
            parent_message_id=parent_message_id,
            model_name=get_settings().openai_model if role is MessageRole.ASSISTANT else None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            latency_ms=None,
            error_code=None,
            metadata=metadata,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        return await self._message_repository.add(message)


def _to_stream_message(message: Message) -> ChatStreamMessage:
    role = "user" if message.role is MessageRole.USER else "assistant"
    return ChatStreamMessage(
        id=message.id,
        role=role,
        content=message.content,
        sequence_no=message.sequence_no,
        created_at=message.created_at,
    )


def _load_agent_context(metadata: dict[str, object]) -> AgentConversationContext:
    payload = metadata.get("agent_context")
    if not isinstance(payload, dict):
        return AgentConversationContext()

    try:
        return AgentConversationContext.model_validate(payload)
    except Exception:
        logger.warning("invalid agent context metadata ignored", exc_info=True)
        return AgentConversationContext()


def _build_title(message: str) -> str:
    normalized = " ".join(message.strip().split())
    return normalized[:40] or "새 채팅"


def _chunk_text(text: str, *, chunk_size: int = 24) -> list[str]:
    return [
        text[index : index + chunk_size]
        for index in range(0, len(text), chunk_size)
    ]
