from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_session_service
from app.core.config import Settings, get_settings
from app.domains.auth.controller.router import router as auth_router
from app.domains.auth.domain.exceptions import InvalidProfileUpdateError
from app.domains.auth.infrastructure.repositories import (
    NicknameAlreadyExistsError,
)
from app.domains.auth.service.dto import CurrentUserDto, SupabaseAuthUserDto
from app.domains.auth.service.services import AuthSessionService

AUTH_USER_ID = UUID("11111111-1111-4111-8111-111111111111")
PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")


class FakeSupabaseAuthClient:
    async def get_user(self, access_token: str) -> SupabaseAuthUserDto:
        assert access_token == "access-token"
        return SupabaseAuthUserDto(id=AUTH_USER_ID, email="fan@example.com")


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeUserProfileRepository:
    def __init__(self, profile: CurrentUserDto | None = None) -> None:
        self.profile = profile or CurrentUserDto(
            id=PROFILE_ID,
            auth_user_id=AUTH_USER_ID,
            nickname="old-name",
            favorite_team=None,
        )
        self.last_update: dict[str, object] | None = None

    async def find_by_auth_user_id(
        self,
        auth_user_id: UUID,
    ) -> CurrentUserDto | None:
        if self.profile is None or self.profile.auth_user_id != auth_user_id:
            return None
        return self.profile

    async def update_profile(
        self,
        *,
        profile_id: UUID,
        nickname: str | None,
        favorite_team: str | None,
        update_favorite_team: bool,
    ) -> CurrentUserDto | None:
        self.last_update = {
            "profile_id": profile_id,
            "nickname": nickname,
            "favorite_team": favorite_team,
            "update_favorite_team": update_favorite_team,
        }
        if self.profile is None or self.profile.id != profile_id:
            return None
        if nickname == "duplicate":
            raise NicknameAlreadyExistsError

        updated = CurrentUserDto(
            id=self.profile.id,
            auth_user_id=self.profile.auth_user_id,
            nickname=nickname if nickname is not None else self.profile.nickname,
            favorite_team=(
                favorite_team if update_favorite_team else self.profile.favorite_team
            ),
        )
        self.profile = updated
        return updated


def make_service(
    repository: FakeUserProfileRepository,
    session: FakeSession,
) -> AuthSessionService:
    return AuthSessionService(
        supabase_auth_client=FakeSupabaseAuthClient(),
        user_profile_repository=repository,
        session=session,
    )


def make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
        openai_api_key="test-openai-key",
    )
    return app


@pytest.mark.asyncio
async def test_update_current_user_trims_nickname_and_normalizes_team() -> None:
    repository = FakeUserProfileRepository()
    session = FakeSession()
    service = make_service(repository, session)

    user = await service.update_current_user(
        access_token="access-token",
        nickname="  new-name  ",
        favorite_team="lotte",
        update_favorite_team=True,
    )

    assert user.nickname == "new-name"
    assert user.favorite_team == "LOTTE"
    assert repository.last_update == {
        "profile_id": PROFILE_ID,
        "nickname": "new-name",
        "favorite_team": "LOTTE",
        "update_favorite_team": True,
    }
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_update_current_user_rejects_blank_nickname() -> None:
    repository = FakeUserProfileRepository()
    session = FakeSession()
    service = make_service(repository, session)

    with pytest.raises(InvalidProfileUpdateError, match="nickname_required"):
        await service.update_current_user(
            access_token="access-token",
            nickname="   ",
            favorite_team=None,
            update_favorite_team=False,
        )

    assert repository.last_update is None
    assert session.commits == 0
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_update_current_user_rejects_unknown_favorite_team() -> None:
    repository = FakeUserProfileRepository()
    session = FakeSession()
    service = make_service(repository, session)

    with pytest.raises(InvalidProfileUpdateError, match="invalid_favorite_team"):
        await service.update_current_user(
            access_token="access-token",
            nickname=None,
            favorite_team="BUSAN",
            update_favorite_team=True,
        )

    assert repository.last_update is None
    assert session.commits == 0
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_update_current_user_rolls_back_duplicate_nickname() -> None:
    repository = FakeUserProfileRepository()
    session = FakeSession()
    service = make_service(repository, session)

    with pytest.raises(NicknameAlreadyExistsError):
        await service.update_current_user(
            access_token="access-token",
            nickname="duplicate",
            favorite_team=None,
            update_favorite_team=False,
        )

    assert session.commits == 0
    assert session.rollbacks == 1


def test_patch_me_returns_updated_user_response() -> None:
    app = make_test_app()

    class FakeAuthSessionService:
        async def update_current_user(
            self,
            *,
            access_token: str,
            nickname: str | None,
            favorite_team: str | None,
            update_favorite_team: bool,
        ) -> CurrentUserDto:
            assert access_token == "access-token"
            assert nickname == "  새닉네임  "
            assert favorite_team is None
            assert update_favorite_team is True
            return CurrentUserDto(
                id=uuid4(),
                auth_user_id=AUTH_USER_ID,
                nickname="새닉네임",
                favorite_team=None,
            )

    app.dependency_overrides[get_auth_session_service] = FakeAuthSessionService
    client = TestClient(app)
    response = client.patch(
        "/api/v1/auth/me",
        json={"nickname": "  새닉네임  ", "favoriteTeam": None},
        cookies={"nb_access_token": "access-token"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["nickname"] == "새닉네임"
    assert response.json()["user"]["favoriteTeam"] is None


def test_patch_me_returns_conflict_for_duplicate_nickname() -> None:
    app = make_test_app()

    class FakeAuthSessionService:
        async def update_current_user(
            self,
            *,
            access_token: str,
            nickname: str | None,
            favorite_team: str | None,
            update_favorite_team: bool,
        ) -> CurrentUserDto:
            raise NicknameAlreadyExistsError

    app.dependency_overrides[get_auth_session_service] = FakeAuthSessionService

    client = TestClient(app)
    response = client.patch(
        "/api/v1/auth/me",
        json={"nickname": "duplicate"},
        cookies={"nb_access_token": "access-token"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "nickname_already_exists"}


def test_patch_me_requires_access_token_cookie() -> None:
    app = make_test_app()

    client = TestClient(app)
    response = client.patch("/api/v1/auth/me", json={"nickname": "new-name"})

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthenticated"}
