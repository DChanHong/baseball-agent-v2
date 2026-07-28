from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.database import get_db_session
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="New Baseball API",
    version="0.1.0",
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
