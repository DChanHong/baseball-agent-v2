from uuid import UUID

from pydantic import BaseModel, Field


class CurrentUserResponseUser(BaseModel):
    """Current user payload nested under the user key."""

    id: UUID
    nickname: str
    favoriteTeam: str | None


class CurrentUserResponse(BaseModel):
    """Response body for GET /auth/me."""

    user: CurrentUserResponseUser


class UpdateCurrentUserRequest(BaseModel):
    """Request body for PATCH /auth/me."""

    nickname: str | None = Field(default=None, max_length=32)
    favoriteTeam: str | None = Field(default=None, max_length=30)
