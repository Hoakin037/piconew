from fastapi import APIRouter

from app.modules import auth, chats, file_roter, messages, users

router = APIRouter(prefix="/api")
router.include_router(auth)
router.include_router(chats)
router.include_router(messages, prefix="/chats")
router.include_router(users)
router.include_router(file_roter)
