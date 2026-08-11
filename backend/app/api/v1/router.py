from fastapi import APIRouter

from app.domains.auth.controller.router import (
    router as auth_router,
)
from app.domains.baseball.controller.router import (
    router as baseball_router,
)
from app.domains.chat.controller.router import (
    router as chat_router,
)
from app.domains.conversation.controller.router import (
    router as conversation_router,
)

router = APIRouter()
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(baseball_router)
router.include_router(conversation_router)
