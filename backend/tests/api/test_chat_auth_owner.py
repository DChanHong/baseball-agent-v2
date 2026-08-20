from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.routing_schemas import (
    DirectAnswerIntent,
    FindKboGameRoutingArgs,
    ToolRoutingDecision,
)
from app.api.dependencies import get_auth_session_service, get_chat_stream_service
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.baseball.domain.enums import KboGameStatus
from app.domains.baseball.tool.find_kbo_game.schemas import (
    FindKboGameToolResult,
    KboGameToolResultItem,
)
from app.domains.chat.controller.router import router as chat_router
from app.domains.chat.controller.schemas import ChatStreamRequest
from app.domains.chat.service.services import ChatStreamService
from app.domains.conversation.domain.entities import Conversation, Message

PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")
AUTH_USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeConversationRepository:
    def __init__(self) -> None:
        self.conversations: dict[UUID, Conversation] = {}
        self.added: list[Conversation] = []
        self.saved: list[Conversation] = []

    async def add(self, conversation: Conversation) -> Conversation:
        self.conversations[conversation.id] = conversation
        self.added.append(conversation)
        return conversation

    async def find_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self.conversations.get(conversation_id)

    async def save(self, conversation: Conversation) -> Conversation:
        self.conversations[conversation.id] = conversation
        self.saved.append(conversation)
        return conversation


class FakeMessageRepository:
    def __init__(self) -> None:
        self.messages: dict[UUID, Message] = {}
        self.added: list[Message] = []
        self.saved: list[Message] = []

    async def add(self, message: Message) -> Message:
        self.messages[message.id] = message
        self.added.append(message)
        return message

    async def save(self, message: Message) -> Message:
        self.messages[message.id] = message
        self.saved.append(message)
        return message

    async def get_next_sequence_no(self, conversation_id: UUID) -> int:
        return (
            max(
                (
                    message.sequence_no
                    for message in self.messages.values()
                    if message.conversation_id == conversation_id
                ),
                default=0,
            )
            + 1
        )


class FakeRoutingService:
    def __init__(self, decisions: list[ToolRoutingDecision] | None = None) -> None:
        self.favorite_team_id: str | None = None
        self.user_contexts = []
        self.decisions = decisions or [_direct_decision()]

    async def execute(self, *, message: str, user_context):
        self.favorite_team_id = user_context.favorite_team_id
        self.user_contexts.append(user_context)
        if not self.decisions:
            raise AssertionError("unexpected routing call")
        return self.decisions.pop(0)


class FakeToolExecutor:
    def __init__(self, result: FindKboGameToolResult | None = None) -> None:
        self.result = result
        self.calls = 0

    async def execute(self, decision: ToolRoutingDecision):
        self.calls += 1
        if self.result is None:
            raise AssertionError("unexpected tool execution")
        return self.result


def make_current_user() -> CurrentUserDto:
    return CurrentUserDto(
        id=PROFILE_ID,
        auth_user_id=AUTH_USER_ID,
        nickname="fan",
        favorite_team="LOTTE",
    )


def _direct_decision(
    direct_answer_intent: DirectAnswerIntent | None = None,
) -> ToolRoutingDecision:
    return ToolRoutingDecision(
        is_in_scope=True,
        should_call_tool=False,
        tool_name=None,
        args=None,
        needs_clarification=False,
        clarification_reason=None,
        unsupported_reason=None,
        direct_answer_intent=direct_answer_intent,
    )


def _find_lotte_game_decision() -> ToolRoutingDecision:
    return ToolRoutingDecision(
        is_in_scope=True,
        should_call_tool=True,
        tool_name="find_kbo_game",
        args=FindKboGameRoutingArgs(
            team_id="LOTTE",
            date=date(2026, 8, 14),
            date_from=None,
            date_to=None,
        ),
        needs_clarification=False,
        clarification_reason=None,
        unsupported_reason=None,
    )


def _single_lotte_game_result() -> FindKboGameToolResult:
    return FindKboGameToolResult(
        total=1,
        games=[
            KboGameToolResultItem(
                id=UUID("33333333-3333-4333-8333-333333333333"),
                season_year=2026,
                source_game_id="20260814LTHT",
                internal_game_key="2026-08-14-LOTTE-HANWHA",
                game_date=date(2026, 8, 14),
                start_time=time(18, 30),
                starts_at=datetime(2026, 8, 14, 9, 30, tzinfo=UTC),
                away_team_id="LOTTE",
                home_team_id="HANWHA",
                stadium_id="DAEJEON",
                away_team_name="롯데",
                home_team_name="한화",
                stadium_name="대전 한화생명 볼파크",
                game_status=KboGameStatus.SCHEDULED,
                status_reason=None,
                away_score=None,
                home_score=None,
                source_name="KBO",
                source_url="https://www.koreabaseball.com/",
                source_collected_at=datetime(2026, 8, 14, tzinfo=UTC),
            )
        ],
    )


@pytest.mark.asyncio
async def test_chat_stream_stores_new_conversation_and_messages_by_profile_id() -> None:
    conversation_repository = FakeConversationRepository()
    message_repository = FakeMessageRepository()
    routing_service = FakeRoutingService()
    session = FakeSession()
    service = ChatStreamService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        tool_routing_service=routing_service,
        tool_executor=FakeToolExecutor(),
        session=session,
    )

    events = [
        event
        async for event in service.stream(
            ChatStreamRequest(conversation_id=None, message="오늘 경기 있어?"),
            current_user=make_current_user(),
        )
    ]

    assert any(event.startswith("event: done\n") for event in events)
    assert conversation_repository.added[0].user_profile_id == PROFILE_ID
    assert conversation_repository.added[0].guest_id is None
    assert {message.user_profile_id for message in message_repository.added} == {
        PROFILE_ID
    }
    assert routing_service.favorite_team_id == "LOTTE"
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_chat_stream_uses_selected_game_context_for_follow_up_place() -> None:
    conversation_repository = FakeConversationRepository()
    message_repository = FakeMessageRepository()
    routing_service = FakeRoutingService(
        decisions=[
            _find_lotte_game_decision(),
            _direct_decision("selected_game_place"),
        ]
    )
    tool_executor = FakeToolExecutor(result=_single_lotte_game_result())
    session = FakeSession()
    service = ChatStreamService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        tool_routing_service=routing_service,
        tool_executor=tool_executor,
        session=session,
    )

    first_events = [
        event
        async for event in service.stream(
            ChatStreamRequest(conversation_id=None, message="롯데 오늘 야구 일정 알려줘"),
            current_user=make_current_user(),
        )
    ]
    conversation = conversation_repository.added[0]
    saved_conversation = conversation_repository.conversations[conversation.id]

    assert any(event.startswith("event: tool.started\n") for event in first_events)
    assert any(event.startswith("event: tool.completed\n") for event in first_events)
    assert tool_executor.calls == 1
    assert "8월 14일 롯데 경기는 18:30" in message_repository.saved[-1].content
    assert "한화와 예정되어 있습니다" in message_repository.saved[-1].content
    assert saved_conversation.metadata["agent_context"]["selected_game"][
        "stadium_name"
    ] == "대전 한화생명 볼파크"
    assert (
        saved_conversation.metadata["agent_context"]["selected_team_id"]
        == "LOTTE"
    )

    second_events = [
        event
        async for event in service.stream(
            ChatStreamRequest(
                conversation_id=conversation.id,
                message="어디서 경기하는거지?",
            ),
            current_user=make_current_user(),
        )
    ]
    second_assistant_message = message_repository.saved[-1]

    assert not any(event.startswith("event: tool.started\n") for event in second_events)
    assert tool_executor.calls == 1
    assert len(routing_service.user_contexts) == 2
    assert (
        routing_service.user_contexts[-1].conversation_context.selected_game.stadium_id
        == "DAEJEON"
    )
    assert "대전 한화생명 볼파크" in second_assistant_message.content
    assert second_assistant_message.metadata["agent_context"]["selected_game"][
        "stadium_id"
    ] == "DAEJEON"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "direct_answer_intent", "expected_parts"),
    [
        ("몇 시야?", "selected_game_time", ("18:30", "시작합니다")),
        ("상대가 누구야?", "selected_game_opponent", ("롯데의 상대는 한화",)),
        ("홈 경기야?", "selected_game_home_away", ("롯데는 원정 경기", "한화 홈 경기")),
        ("상태가 뭐야?", "selected_game_status", ("예정 상태",)),
        ("오늘 취소됐어?", "selected_game_status", ("예정 상태",)),
    ],
)
async def test_chat_stream_uses_selected_game_context_for_follow_up_details(
    message: str,
    direct_answer_intent: DirectAnswerIntent,
    expected_parts: tuple[str, ...],
) -> None:
    conversation_repository = FakeConversationRepository()
    message_repository = FakeMessageRepository()
    routing_service = FakeRoutingService(
        decisions=[
            _find_lotte_game_decision(),
            _direct_decision(direct_answer_intent),
        ]
    )
    tool_executor = FakeToolExecutor(result=_single_lotte_game_result())
    session = FakeSession()
    service = ChatStreamService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        tool_routing_service=routing_service,
        tool_executor=tool_executor,
        session=session,
    )

    async for _ in service.stream(
        ChatStreamRequest(conversation_id=None, message="롯데 오늘 야구 일정 알려줘"),
        current_user=make_current_user(),
    ):
        pass
    conversation = conversation_repository.added[0]

    follow_up_events = [
        event
        async for event in service.stream(
            ChatStreamRequest(
                conversation_id=conversation.id,
                message=message,
            ),
            current_user=make_current_user(),
        )
    ]
    assistant_message = message_repository.saved[-1]

    assert not any(
        event.startswith("event: tool.started\n") for event in follow_up_events
    )
    assert tool_executor.calls == 1
    assert len(routing_service.user_contexts) == 2
    assert (
        routing_service.user_contexts[-1].conversation_context.selected_team_id
        == "LOTTE"
    )
    for expected_part in expected_parts:
        assert expected_part in assistant_message.content


def test_chat_endpoint_requires_login_before_streaming() -> None:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")
    app.dependency_overrides[get_chat_stream_service] = lambda: object()
    app.dependency_overrides[get_auth_session_service] = lambda: object()

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "오늘 경기 있어?"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthenticated"}
