from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.domains.auth.service.services import AuthRedirectService


def test_google_redirect_keeps_backend_state_out_of_supabase_state() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
        openai_api_key="test-openai-key",
        supabase_url="http://127.0.0.1:54321",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-role-key",
        app_base_url="http://127.0.0.1:4000",
    )

    oauth_start = AuthRedirectService(settings).build_google_redirect()

    authorize_url = urlparse(oauth_start.redirect_url)
    authorize_query = parse_qs(authorize_url.query)
    redirect_to = authorize_query["redirect_to"][0]
    redirect_query = parse_qs(urlparse(redirect_to).query)

    assert "state" not in authorize_query
    assert authorize_query["provider"] == ["google"]
    assert redirect_query["oauth_state"] == [oauth_start.state]
