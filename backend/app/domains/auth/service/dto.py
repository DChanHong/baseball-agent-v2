from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CurrentUserDto:
    """Authenticated application profile returned to controllers."""

    id: UUID
    auth_user_id: UUID
    nickname: str
    favorite_team: str | None


@dataclass(frozen=True, slots=True)
class SupabaseAuthUserDto:
    """User identity returned by Supabase Auth."""

    id: UUID
    email: str | None


@dataclass(frozen=True, slots=True)
class SupabaseSessionDto:
    """Supabase Auth session tokens used for HttpOnly cookies."""

    access_token: str
    refresh_token: str
    expires_in: int
    user: SupabaseAuthUserDto
