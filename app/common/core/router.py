from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.common.core.jwt import get_current_user
from app.modules import auth, chats

router = APIRouter(prefix="/api")
router.include_router(auth)
router.include_router(chats)


@router.get(path="/chatss", status_code=200)
async def check_jwt(current_user: UUID = Depends(get_current_user)):
    if current_user:
        return {"user_id": current_user}
    raise HTTPException(status_code=404, detail="Пользователь не найден")
