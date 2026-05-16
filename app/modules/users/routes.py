from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.common.core.jwt import get_current_user
from app.modules.users import UserDTO, UserService, get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/self", response_model=UserDTO)
async def get_user(
    user_sid: Annotated[UUID, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return await user_service.get_user(user_sid)
