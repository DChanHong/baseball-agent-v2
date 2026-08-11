from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_auth_redirect_service, get_auth_session_service
from app.core.config import Settings, get_settings
from app.domains.auth.controller.schemas import (
    CurrentUserResponse,
    CurrentUserResponseUser,
)
from app.domains.auth.domain.exceptions import (
    AuthConfigurationError,
    UnauthenticatedError,
)
from app.domains.auth.service.dto import CurrentUserDto, SupabaseSessionDto
from app.domains.auth.service.services import AuthRedirectService, AuthSessionService

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

AuthRedirectServiceDependency = Annotated[
    AuthRedirectService,
    Depends(get_auth_redirect_service),
]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
AuthSessionServiceDependency = Annotated[
    AuthSessionService,
    Depends(get_auth_session_service),
]


@router.get("/google", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def start_google_oauth(
    service: AuthRedirectServiceDependency,
    settings: SettingsDependency,
) -> RedirectResponse:
    """Redirect the browser to Supabase Google OAuth."""

    try:
        oauth_start = service.build_google_redirect()
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_configured",
        ) from exc

    response = RedirectResponse(oauth_start.redirect_url)
    _set_temporary_cookie(
        response,
        settings=settings,
        key=settings.auth_oauth_state_cookie_name,
        value=oauth_start.state,
    )
    _set_temporary_cookie(
        response,
        settings=settings,
        key=settings.auth_oauth_verifier_cookie_name,
        value=oauth_start.code_verifier,
    )
    return response


@router.get("/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def handle_auth_callback(
    request: Request,
    service: AuthSessionServiceDependency,
    settings: SettingsDependency,
) -> RedirectResponse:
    """Exchange Supabase OAuth code for a backend-managed cookie session."""

    error = request.query_params.get("error")
    if error is not None:
        return RedirectResponse(f"{settings.frontend_app_url}?auth=error")

    auth_code = request.query_params.get("code")
    returned_state = request.query_params.get("state")
    expected_state = request.cookies.get(settings.auth_oauth_state_cookie_name)
    code_verifier = request.cookies.get(settings.auth_oauth_verifier_cookie_name)

    if (
        not auth_code
        or not returned_state
        or not expected_state
        or not code_verifier
        or returned_state != expected_state
    ):
        return RedirectResponse(f"{settings.frontend_app_url}?auth=invalid_callback")

    try:
        session, _ = await service.complete_oauth_callback(
            auth_code=auth_code,
            code_verifier=code_verifier,
        )
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_configured",
        ) from exc

    response = RedirectResponse(settings.frontend_app_url)
    _set_auth_cookies(response, settings=settings, session=session)
    _delete_temporary_cookies(response, settings=settings)
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    request: Request,
    service: AuthSessionServiceDependency,
) -> CurrentUserResponse:
    """Return the current authenticated application profile."""

    access_token = request.cookies.get(get_settings().auth_access_cookie_name)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        )

    try:
        user = await service.get_current_user(access_token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        ) from exc

    return to_current_user_response(user)


@router.post("/refresh", response_model=CurrentUserResponse)
async def refresh_session(
    request: Request,
    response: Response,
    service: AuthSessionServiceDependency,
    settings: SettingsDependency,
) -> CurrentUserResponse:
    """Refresh the Supabase session from the HttpOnly refresh cookie."""

    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        )

    try:
        session, user = await service.refresh_session(refresh_token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthenticated",
        ) from exc

    _set_auth_cookies(response, settings=settings, session=session)
    return to_current_user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    settings: SettingsDependency,
) -> None:
    """Clear auth cookies for the browser."""

    response.delete_cookie(
        settings.auth_access_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )
    response.delete_cookie(
        settings.auth_refresh_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


@router.patch("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_current_user() -> None:
    """Profile update placeholder for the next Auth implementation units."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="auth_profile_update_not_implemented",
    )


@router.delete("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_current_user() -> None:
    """Account deletion placeholder for the final backend Auth unit."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="auth_delete_not_implemented",
    )


def to_current_user_response(user: CurrentUserDto) -> CurrentUserResponse:
    """Convert an application user DTO into the public API schema."""

    return CurrentUserResponse(
        user=CurrentUserResponseUser(
            id=user.id,
            nickname=user.nickname,
            favoriteTeam=user.favorite_team,
        )
    )


def _set_auth_cookies(
    response: Response,
    *,
    settings: Settings,
    session: SupabaseSessionDto,
) -> None:
    response.set_cookie(
        settings.auth_access_cookie_name,
        session.access_token,
        max_age=session.expires_in,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )
    response.set_cookie(
        settings.auth_refresh_cookie_name,
        session.refresh_token,
        max_age=settings.auth_refresh_cookie_max_age_seconds,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


def _set_temporary_cookie(
    response: Response,
    *,
    settings: Settings,
    key: str,
    value: str,
) -> None:
    response.set_cookie(
        key,
        value,
        max_age=600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


def _delete_temporary_cookies(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        settings.auth_oauth_state_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )
    response.delete_cookie(
        settings.auth_oauth_verifier_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )
