from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "New Baseball API"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 4000
    app_debug: bool = True
    api_response_logging_enabled: bool = True
    api_response_log_dir: str = "logs/api-responses"
    api_response_log_max_body_bytes: int = 1_000_000
    cors_allow_origins: str = (
        "http://127.0.0.1:3001,"
        "http://localhost:3001,"
        "http://127.0.0.1:3000,"
        "http://localhost:3000"
    )
    database_url: str

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = 30.0

    # KMA short-term forecast API
    kma_api_endpoint: str = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    kma_service_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
