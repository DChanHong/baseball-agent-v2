import base64
import hashlib
import secrets
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.domains.auth.domain.exceptions import (
    AuthConfigurationError,
    InvalidProfileUpdateError,
    UnauthenticatedError,
)
from app.domains.auth.infrastructure.repositories import (
    NicknameAlreadyExistsError,
    SqlAlchemyUserProfileRepository,
)
from app.domains.auth.infrastructure.supabase_auth_client import SupabaseAuthClient
from app.domains.auth.service.dto import CurrentUserDto, SupabaseSessionDto


class OAuthStartDto:
    """OAuth redirect URL plus temporary values that must be persisted in cookies."""

    def __init__(
        self,
        *,
        redirect_url: str,
        state: str,
        code_verifier: str,
    ) -> None:
        self.redirect_url = redirect_url
        self.state = state
        self.code_verifier = code_verifier


class AuthRedirectService:
    """Builds provider redirect URLs for Hosted Supabase Auth."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_google_redirect(self) -> OAuthStartDto:
        """Return the Supabase Google OAuth start URL and backend OAuth state."""

        self._ensure_configured()
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = _build_code_challenge(code_verifier)
        redirect_to = (
            f"{self._settings.app_base_url}/api/v1/auth/callback?"
            f"{urlencode({'oauth_state': state})}"
        )
        query = urlencode(
            {
                "provider": "google",
                "redirect_to": redirect_to,
                "flow_type": "pkce",
                "scopes": "email profile",
                "code_challenge": code_challenge,
                "code_challenge_method": "s256",
            }
        )
        redirect_url = (
            f"{self._settings.supabase_url.rstrip('/')}/auth/v1/authorize?{query}"
        )

        return OAuthStartDto(
            redirect_url=redirect_url,
            state=state,
            code_verifier=code_verifier,
        )

    def _ensure_configured(self) -> None:
        if not self._settings.supabase_url:
            raise AuthConfigurationError("SUPABASE_URL is required.")
        if not self._settings.supabase_anon_key:
            raise AuthConfigurationError("SUPABASE_ANON_KEY is required.")


class AuthSessionService:
    """Coordinates Supabase Auth sessions and application profiles."""

    _kbo_team_ids = frozenset(
        {
            "LG",
            "DOOSAN",
            "KIWOOM",
            "SSG",
            "KT",
            "KIA",
            "SAMSUNG",
            "LOTTE",
            "HANWHA",
            "NC",
        }
    )
    _nickname_prefixes = (
        "직관러",
        "야구친구",
        "불펜탐험가",
        "응원단짝",
        "야구산책러",
    )

    def __init__(
        self,
        *,
        supabase_auth_client: SupabaseAuthClient,
        user_profile_repository: SqlAlchemyUserProfileRepository,
        session: AsyncSession,
    ) -> None:
        self._supabase_auth_client = supabase_auth_client
        self._user_profile_repository = user_profile_repository
        self._session = session

    async def complete_oauth_callback(
        self,
        *,
        auth_code: str,
        code_verifier: str,
    ) -> tuple[SupabaseSessionDto, CurrentUserDto]:
        try:
            session = await self._supabase_auth_client.exchange_code_for_session(
                auth_code=auth_code,
                code_verifier=code_verifier,
            )
            profile = await self._get_or_create_profile(
                auth_user_id=session.user.id,
                email=session.user.email,
            )
            await self._session.commit()
            return session, profile
        except Exception:
            await self._session.rollback()
            raise

    async def get_current_user(self, access_token: str) -> CurrentUserDto:
        auth_user = await self._supabase_auth_client.get_user(access_token)
        profile = await self._user_profile_repository.find_by_auth_user_id(
            auth_user.id
        )

        if profile is None:
            raise UnauthenticatedError("Application profile was not found.")

        return profile

    async def update_current_user(
        self,
        *,
        access_token: str,
        nickname: str | None,
        favorite_team: str | None,
        update_favorite_team: bool,
    ) -> CurrentUserDto:
        normalized_nickname = self._normalize_nickname(nickname)
        normalized_favorite_team = self._normalize_favorite_team(favorite_team)

        try:
            auth_user = await self._supabase_auth_client.get_user(access_token)
            profile = await self._user_profile_repository.find_by_auth_user_id(
                auth_user.id
            )

            if profile is None:
                raise UnauthenticatedError("Application profile was not found.")

            updated_profile = await self._user_profile_repository.update_profile(
                profile_id=profile.id,
                nickname=normalized_nickname,
                favorite_team=normalized_favorite_team,
                update_favorite_team=update_favorite_team,
            )
            if updated_profile is None:
                raise UnauthenticatedError("Application profile was not found.")

            await self._session.commit()
            return updated_profile
        except Exception:
            await self._session.rollback()
            raise

    async def refresh_session(
        self,
        refresh_token: str,
    ) -> tuple[SupabaseSessionDto, CurrentUserDto]:
        try:
            session = await self._supabase_auth_client.refresh_session(refresh_token)
            profile = await self._get_or_create_profile(
                auth_user_id=session.user.id,
                email=session.user.email,
            )
            await self._session.commit()
            return session, profile
        except Exception:
            await self._session.rollback()
            raise

    async def _get_or_create_profile(
        self,
        *,
        auth_user_id: UUID,
        email: str | None,
    ) -> CurrentUserDto:
        profile = await self._user_profile_repository.find_by_auth_user_id(
            auth_user_id
        )
        if profile is not None:
            await self._user_profile_repository.touch_last_login_at(profile.id)
            return profile

        for _ in range(10):
            try:
                return await self._user_profile_repository.create(
                    auth_user_id=auth_user_id,
                    nickname=self._generate_nickname(),
                    encrypted_email=None,
                )
            except NicknameAlreadyExistsError:
                continue

        raise RuntimeError("Failed to generate a unique nickname.")

    def _generate_nickname(self) -> str:
        prefix = secrets.choice(self._nickname_prefixes)
        suffix = secrets.randbelow(9000) + 1000
        return f"{prefix}-{suffix}"

    @staticmethod
    def _normalize_nickname(nickname: str | None) -> str | None:
        if nickname is None:
            return None

        normalized = nickname.strip()
        if not normalized:
            raise InvalidProfileUpdateError("nickname_required")

        return normalized

    @classmethod
    def _normalize_favorite_team(cls, favorite_team: str | None) -> str | None:
        if favorite_team is None:
            return None

        normalized = favorite_team.strip().upper()
        if normalized not in cls._kbo_team_ids:
            raise InvalidProfileUpdateError("invalid_favorite_team")

        return normalized


def _build_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
