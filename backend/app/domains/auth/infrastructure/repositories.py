from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.infrastructure.models import UserProfileModel
from app.domains.auth.service.dto import CurrentUserDto


class NicknameAlreadyExistsError(RuntimeError):
    """Raised when a generated or requested nickname already exists."""


class SqlAlchemyUserProfileRepository:
    """PostgreSQL을 사용하는 사용자 프로필 Repository 구현체입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_auth_user_id(
        self,
        auth_user_id: UUID,
    ) -> CurrentUserDto | None:
        statement = select(UserProfileModel).where(
            UserProfileModel.auth_user_id == auth_user_id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dto(model)

    async def create(
        self,
        *,
        auth_user_id: UUID,
        nickname: str,
        encrypted_email: str | None,
    ) -> CurrentUserDto:
        now = datetime.now(UTC)
        model = UserProfileModel(
            auth_user_id=auth_user_id,
            encrypted_email=encrypted_email,
            nickname=nickname,
            favorite_team=None,
            last_login_at=now,
        )
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise NicknameAlreadyExistsError from exc

        await self._session.refresh(model)
        return self._to_dto(model)

    async def touch_last_login_at(self, profile_id: UUID) -> None:
        statement = select(UserProfileModel).where(UserProfileModel.id == profile_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return

        model.last_login_at = datetime.now(UTC)
        await self._session.flush()

    async def update_profile(
        self,
        *,
        profile_id: UUID,
        nickname: str | None,
        favorite_team: str | None,
        update_favorite_team: bool,
    ) -> CurrentUserDto | None:
        statement = select(UserProfileModel).where(UserProfileModel.id == profile_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        if nickname is not None:
            model.nickname = nickname
        if update_favorite_team:
            model.favorite_team = favorite_team

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise NicknameAlreadyExistsError from exc

        await self._session.refresh(model)
        return self._to_dto(model)

    @staticmethod
    def _to_dto(model: UserProfileModel) -> CurrentUserDto:
        return CurrentUserDto(
            id=model.id,
            auth_user_id=model.auth_user_id,
            nickname=model.nickname,
            favorite_team=model.favorite_team,
        )
