from fastapi import APIRouter

from app.domains.conversation.controller.router import (
    router as conversation_router,
)

router = APIRouter()
router.include_router(conversation_router)
