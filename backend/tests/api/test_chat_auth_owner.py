from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.routing_schemas import ToolRoutingDecision
from app.api.dependencies import get_auth_session_service, get_chat_stream_service
from app.domains.auth.service.dto import CurrentUserDto
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
    def __init__(self) -> None:
        self.favorite_team_id: str | None = None

    async def execute(self, *, message: str, user_context):
        self.favorite_team_id = user_context.favorite_team_id
        return ToolRoutingDecision(
            is_in_scope=True,
            should_call_tool=False,
            tool_name=None,
            args=None,
            needs_clarification=False,
            clarification_reason=None,
            unsupported_reason=None,
        )


class FakeToolExecutor:
    pass


def make_current_user() -> CurrentUserDto:
    return CurrentUserDto(
        id=PROFILE_ID,
        auth_user_id=AUTH_USER_ID,
        nickname="fan",
        favorite_team="LOTTE",
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
