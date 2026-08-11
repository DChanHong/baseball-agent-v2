from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.routing_schemas import ToolRoutingDecision, ToolRoutingUserContext
from app.agent.routing_service import ToolRoutingService
from app.agent.tool_executor import AgentToolExecutor
from app.core.config import get_settings
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
    ToolName,
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
        tool_routing_service: ToolRoutingService,
        tool_executor: AgentToolExecutor,
        session: AsyncSession,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository
        self._tool_routing_service = tool_routing_service
        self._tool_executor = tool_executor
        self._session = session

    async def stream(self, request: ChatStreamRequest) -> AsyncIterator[str]:
        """Execute one chat request and yield encoded SSE event chunks."""

        try:
            async for event in self._stream_inner(request):
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

    async def _stream_inner(self, request: ChatStreamRequest) -> AsyncIterator[str]:
        now = datetime.now(UTC)
        conversation, created = await self._get_or_create_conversation(
            guest_id=request.guest_id,
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
        )
        await self._session.commit()

        yield encode_sse_event(
            "message.created",
            MessageCreatedEvent(message=_to_stream_message(assistant_message)),
        )

        started_at = perf_counter()
        decision = await self._route_message(request.message)
        tool_payload: dict[str, object] | None = None
        tool_limitations: list[str] = []

        if decision.should_call_tool and decision.tool_name is not None:
            tool_call_id = f"tool_{uuid4().hex[:12]}"
            tool_input = _tool_input_payload(decision)

            yield encode_sse_event(
                "tool.started",
                ToolStartedEvent(
                    tool_call_id=tool_call_id,
                    name=decision.tool_name,
                    status="running",
                    input=tool_input,
                ),
            )

            try:
                result = await self._tool_executor.execute(decision)
            except Exception as exc:
                logger.exception("tool execution failed tool_name=%s", decision.tool_name)
                yield encode_sse_event(
                    "tool.failed",
                    ToolFailedEvent(
                        tool_call_id=tool_call_id,
                        name=decision.tool_name,
                        status="failed",
                        input=tool_input,
                        error=StreamError(
                            code="tool_execution_failed",
                            message="도구 실행 중 문제가 발생했습니다.",
                        ),
                    ),
                )
                tool_payload = {
                    "tool_call_id": tool_call_id,
                    "name": decision.tool_name,
                    "status": "failed",
                    "input": tool_input,
                    "result": None,
                    "error": {"code": "tool_execution_failed", "message": str(exc)},
                }
            else:
                result_payload = _model_payload(result)
                tool_limitations = _extract_limitations(result_payload)
                yield encode_sse_event(
                    "tool.completed",
                    ToolCompletedEvent(
                        tool_call_id=tool_call_id,
                        name=decision.tool_name,
                        status="completed",
                        input=tool_input,
                        result=result_payload,
                    ),
                )
                tool_payload = {
                    "tool_call_id": tool_call_id,
                    "name": decision.tool_name,
                    "status": "completed",
                    "input": tool_input,
                    "result": result_payload,
                    "error": None,
                }

        assistant_content = _build_assistant_content(
            message=request.message,
            decision=decision,
            tool_payload=tool_payload,
        )

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
                "routing_decision": decision.model_dump(mode="json"),
                "tool_results": [tool_payload] if tool_payload is not None else [],
                "limitations": tool_limitations,
            },
            updated_at=completed_at,
        )
        assistant_message = await self._message_repository.save(assistant_message)

        conversation = replace(
            conversation,
            title=conversation.title or _build_title(request.message),
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
        guest_id: UUID,
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
            if conversation.guest_id != guest_id:
                raise ValueError("conversation does not belong to guest")
            return conversation, False

        conversation = Conversation(
            id=uuid4(),
            user_id=None,
            user_profile_id=None,
            guest_id=guest_id,
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
    ) -> Message:
        now = datetime.now(UTC)
        sequence_no = await self._message_repository.get_next_sequence_no(
            conversation_id
        )
        message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            user_id=None,
            user_profile_id=None,
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

    async def _route_message(self, message: str) -> ToolRoutingDecision:
        today = datetime.now(KST).date()
        return await self._tool_routing_service.execute(
            message=message,
            user_context=ToolRoutingUserContext(
                auth_status="authenticated",
                favorite_team_id=None,
                today=today,
                timezone="Asia/Seoul",
            ),
        )


def _to_stream_message(message: Message) -> ChatStreamMessage:
    role = "user" if message.role is MessageRole.USER else "assistant"
    return ChatStreamMessage(
        id=message.id,
        role=role,
        content=message.content,
        sequence_no=message.sequence_no,
        created_at=message.created_at,
    )


def _tool_input_payload(decision: ToolRoutingDecision) -> dict[str, object]:
    if decision.args is None:
        return {}
    return decision.args.model_dump(mode="json")


def _model_payload(model: BaseModel) -> dict[str, object]:
    return model.model_dump(mode="json")


def _extract_limitations(payload: dict[str, object]) -> list[str]:
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        return []
    return [item for item in limitations if isinstance(item, str)]


def _build_title(message: str) -> str:
    normalized = " ".join(message.strip().split())
    return normalized[:40] or "새 채팅"


def _build_assistant_content(
    *,
    message: str,
    decision: ToolRoutingDecision,
    tool_payload: dict[str, object] | None,
) -> str:
    if decision.needs_clarification:
        return _clarification_text(decision.clarification_reason)

    if decision.unsupported_reason is not None:
        return _unsupported_text(decision.unsupported_reason)

    if not decision.should_call_tool:
        return "질문은 확인했어요. 현재 MVP에서는 사용할 수 있는 도구 범위 안에서 답변을 준비하고 있습니다."

    if tool_payload is None:
        return "도구 호출이 필요했지만 결과를 만들지 못했습니다. 잠시 뒤 다시 시도해 주세요."

    if tool_payload.get("status") == "failed":
        return "도구 실행 중 문제가 생겨서 정확한 결과를 가져오지 못했습니다. 잠시 뒤 다시 시도해 주세요."

    tool_name = tool_payload.get("name")
    result = tool_payload.get("result")
    if not isinstance(tool_name, str) or not isinstance(result, dict):
        return "도구 결과를 확인했습니다."

    return _tool_summary(tool_name=tool_name, result=result, fallback_message=message)


def _clarification_text(reason: str | None) -> str:
    if reason == "team_required_for_schedule_lookup":
        return "어느 팀 경기를 볼지 알려주시면 일정과 경기 여부를 확인해드릴게요."
    if reason == "stadium_required_for_stadium_guide_search":
        return "어느 구장 기준인지 알려주시면 반입, 교통, 시설 정보를 찾아드릴게요."
    if reason == "stadium_required_for_weather_lookup":
        return "어느 구장 날씨를 볼지 알려주시면 직관 컨디션을 확인해드릴게요."
    return "조금만 더 구체적으로 알려주시면 확인해드릴게요."


def _unsupported_text(reason: str) -> str:
    messages = {
        "out_of_scope": "지금은 KBO 직관과 야구 관련 질문만 도와드릴 수 있어요.",
        "weather_or_realtime_cancellation_prediction_required": (
            "공식 우천 취소 여부는 구단/KBO의 확정 공지가 필요해요. "
            "대신 구장 기준 날씨와 직관 준비 수준은 확인할 수 있습니다."
        ),
        "weather_forecast_range_not_supported": "현재 날씨 도구는 오늘부터 글피까지만 지원합니다.",
        "ticket_inventory_tool_required": "실시간 잔여석은 아직 조회할 수 없어요. 예매처와 예매 방법 안내는 가능합니다.",
        "opponent_team_filter_not_supported_yet": "두 팀 맞대결 일정 필터는 아직 지원하지 않습니다.",
    }
    return messages.get(reason, "현재 MVP에서 아직 지원하지 않는 요청입니다.")


def _tool_summary(
    *,
    tool_name: ToolName | str,
    result: dict[str, object],
    fallback_message: str,
) -> str:
    if tool_name == "find_kbo_game":
        total = result.get("total")
        if total == 0:
            return "조회 조건에 맞는 KBO 경기를 찾지 못했어요."
        return f"경기 일정을 조회했습니다. 조건에 맞는 경기는 총 {total}건입니다."

    if tool_name == "get_stadium_info":
        stadium = result.get("stadium")
        if not isinstance(stadium, dict):
            return "구장 정보를 찾지 못했어요."
        name = stadium.get("name_ko") or stadium.get("short_name") or "해당 구장"
        address = stadium.get("address")
        dome_text = "돔구장입니다" if stadium.get("is_dome") else "돔구장은 아닙니다"
        if address:
            return f"{name} 정보를 확인했습니다. 주소는 {address}이고, {dome_text}."
        return f"{name} 정보를 확인했습니다. {dome_text}."

    if tool_name == "get_weather_context":
        stadium_name = result.get("stadium_name") or result.get("stadium_id") or "해당 구장"
        visit_condition = result.get("visit_condition")
        level = None
        if isinstance(visit_condition, dict):
            level = visit_condition.get("level")
        return f"{stadium_name} 기준 날씨 정보를 확인했습니다. 직관 컨디션은 {level or '확인 필요'} 수준입니다."

    if tool_name in {"search_stadium_guide", "search_ticketing_guide"}:
        answerable = result.get("answerable")
        items = result.get("items")
        count = len(items) if isinstance(items, list) else 0
        if not answerable:
            return "관련 안내 문서를 찾지 못했어요. 공식 구단 안내를 함께 확인해 주세요."
        return f"관련 안내 문서 {count}건을 찾았습니다. 카드에서 출처와 주요 내용을 확인할 수 있어요."

    if tool_name == "search_baseball_knowledge":
        answerable = result.get("answerable")
        items = result.get("items")
        count = len(items) if isinstance(items, list) else 0
        if not answerable:
            return "관련 야구 지식 문서를 찾지 못했어요."
        return f"질문 '{fallback_message}'에 참고할 야구 지식 근거 {count}건을 찾았습니다."

    return "도구 결과를 확인했습니다."


def _chunk_text(text: str, *, chunk_size: int = 24) -> list[str]:
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
