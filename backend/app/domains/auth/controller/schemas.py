from uuid import UUID

from pydantic import BaseModel


class CurrentUserResponseUser(BaseModel):
    """Current user payload nested under the user key."""

    id: UUID
    nickname: str
    favoriteTeam: str | None


class CurrentUserResponse(BaseModel):
    """Response body for GET /auth/me."""

    user: CurrentUserResponseUser
