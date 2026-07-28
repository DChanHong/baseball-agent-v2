from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    """OpenAI API 비동기 client를 생성해 재사용합니다."""

    settings = get_settings()

    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )
