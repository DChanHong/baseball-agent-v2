from uuid import UUID

import httpx

from app.core.config import Settings
from app.domains.auth.domain.exceptions import (
    AuthConfigurationError,
    UnauthenticatedError,
)
from app.domains.auth.service.dto import (
    SupabaseAuthUserDto,
    SupabaseSessionDto,
)


class SupabaseAuthClient:
    """Small HTTP client for Supabase Auth endpoints used by the backend."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def exchange_code_for_session(
        self,
        *,
        auth_code: str,
        code_verifier: str,
    ) -> SupabaseSessionDto:
        self._ensure_configured()
        payload = {
            "auth_code": auth_code,
            "code_verifier": code_verifier,
        }
        data = await self._post_json(
            "/auth/v1/token",
            params={"grant_type": "pkce"},
            json=payload,
            use_secret_key=False,
        )
        return self._parse_session(data)

    async def refresh_session(self, refresh_token: str) -> SupabaseSessionDto:
        self._ensure_configured()
        data = await self._post_json(
            "/auth/v1/token",
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
            use_secret_key=False,
        )
        return self._parse_session(data)

    async def get_user(self, access_token: str) -> SupabaseAuthUserDto:
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self._settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": self._settings.supabase_anon_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )

        if response.status_code == 401:
            raise UnauthenticatedError("Supabase session is invalid.")

        response.raise_for_status()
        return self._parse_user(response.json())

    async def _post_json(
        self,
        path: str,
        *,
        params: dict[str, str],
        json: dict[str, str],
        use_secret_key: bool,
    ) -> dict[str, object]:
        api_key = (
            self._settings.supabase_service_role_key
            if use_secret_key
            else self._settings.supabase_anon_key
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._settings.supabase_url.rstrip('/')}{path}",
                params=params,
                headers={
                    "apikey": api_key,
                    "Content-Type": "application/json",
                },
                json=json,
            )

        if response.status_code == 401:
            raise UnauthenticatedError("Supabase session is invalid.")

        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("Unexpected Supabase Auth response.")
        return data

    def _ensure_configured(self) -> None:
        if not self._settings.supabase_url:
            raise AuthConfigurationError("SUPABASE_URL is required.")
        if not self._settings.supabase_anon_key:
            raise AuthConfigurationError("SUPABASE_ANON_KEY is required.")
        if not self._settings.supabase_service_role_key:
            raise AuthConfigurationError("SUPABASE_SERVICE_ROLE_KEY is required.")

    @staticmethod
    def _parse_session(data: dict[str, object]) -> SupabaseSessionDto:
        user_payload = data.get("user")
        if not isinstance(user_payload, dict):
            raise TypeError("Supabase session response does not include a user.")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")

        if not isinstance(access_token, str) or not isinstance(refresh_token, str):
            raise TypeError("Supabase session response does not include tokens.")
        if not isinstance(expires_in, int):
            raise TypeError("Supabase session response does not include expires_in.")

        return SupabaseSessionDto(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=SupabaseAuthClient._parse_user(user_payload),
        )

    @staticmethod
    def _parse_user(data: dict[str, object]) -> SupabaseAuthUserDto:
        user_id = data.get("id")
        email = data.get("email")

        if not isinstance(user_id, str):
            raise TypeError("Supabase user response does not include id.")
        if email is not None and not isinstance(email, str):
            email = None

        return SupabaseAuthUserDto(
            id=UUID(user_id),
            email=email,
        )
