from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_auth_user,
    get_list_conversations_service,
)
from app.domains.auth.service.dto import CurrentUserDto
from app.domains.conversation.controller.router import router as conversation_router
from app.domains.conversation.domain.enums import ConversationStatus
from app.domains.conversation.service.dto import (
    ConversationResultDto,
    ListConversationsQuery,
)

PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")
AUTH_USER_ID = UUID("11111111-1111-4111-8111-111111111111")
CONVERSATION_ID = UUID("33333333-3333-4333-8333-333333333333")


class FakeListConversationsService:
    def __init__(self) -> None:
        self.query: ListConversationsQuery | None = None

    async def execute(
        self,
        query: ListConversationsQuery,
    ) -> list[ConversationResultDto]:
        self.query = query
        now = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

        return [
            ConversationResultDto(
                id=CONVERSATION_ID,
                user_id=None,
                user_profile_id=query.user_profile_id,
                guest_id=None,
                title="잠실 주말 경기 예매와 좌석 추천",
                status=ConversationStatus.ACTIVE,
                agent_type="baseball_general",
                summary=None,
                metadata={},
                last_message_at=now,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
        ]


def make_current_user() -> CurrentUserDto:
    return CurrentUserDto(
        id=PROFILE_ID,
        auth_user_id=AUTH_USER_ID,
        nickname="fan",
        favorite_team="LOTTE",
    )


def test_list_conversations_returns_authenticated_users_conversations() -> None:
    app = FastAPI()
    service = FakeListConversationsService()
    app.include_router(conversation_router, prefix="/api/v1")
    app.dependency_overrides[get_current_auth_user] = make_current_user
    app.dependency_overrides[get_list_conversations_service] = lambda: service

    client = TestClient(app)
    response = client.get("/api/v1/conversations?limit=10&offset=5")

    assert response.status_code == 200
    assert service.query == ListConversationsQuery(
        user_profile_id=PROFILE_ID,
        limit=10,
        offset=5,
    )
    assert response.json()["conversations"] == [
        {
            "id": str(CONVERSATION_ID),
            "user_id": None,
            "user_profile_id": str(PROFILE_ID),
            "guest_id": None,
            "title": "잠실 주말 경기 예매와 좌석 추천",
            "status": "active",
            "agent_type": "baseball_general",
            "summary": None,
            "metadata": {},
            "last_message_at": "2026-08-12T12:00:00Z",
            "created_at": "2026-08-12T12:00:00Z",
            "updated_at": "2026-08-12T12:00:00Z",
            "deleted_at": None,
        }
    ]
