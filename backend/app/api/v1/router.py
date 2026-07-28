from fastapi import APIRouter

from app.domains.baseball.controller.router import (
    router as baseball_router,
)
from app.domains.conversation.controller.router import (
    router as conversation_router,
)

router = APIRouter()
router.include_router(baseball_router)
router.include_router(conversation_router)
