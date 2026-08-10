from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.api_response_logging import ApiResponseLoggingMiddleware
from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title="New Baseball API",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_allow_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    ApiResponseLoggingMiddleware,
    enabled=settings.api_response_logging_enabled,
    log_dir=settings.api_response_log_dir,
    max_body_bytes=settings.api_response_log_max_body_bytes,
)
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "New Baseball API is running",
    }


@app.get("/health/db")
async def database_health_check(
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    await session.execute(text("select 1"))
    return {
        "status": "ok",
        "message": "Database connection is healthy",
    }
