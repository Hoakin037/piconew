from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from  app.modules import auth
from app.common.core.jwt import get_current_user

router = APIRouter(prefix="/api")
router.include_router(auth)

@router.get(path="/chats", status_code=200)
async def check_jwt(current_user: UUID = Depends(get_current_user)):
    if current_user:
        return {"user_id": current_user}
    raise HTTPException(status_code=404, detail="Пользователь не найден")