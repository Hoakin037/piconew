from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.common.core.jwt import get_current_user
from app.common.schemas import Pagination
from app.modules.users import UserDTO, UserService, get_user_service
from app.modules.users.schemas import GetUsersResponse, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/self", response_model=UserDTO)
async def get_user(
    user_sid: Annotated[UUID, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return await user_service.get_user(user_sid)


@router.get("/", response_model=GetUsersResponse)
async def search_users(
    current_user: Annotated[UUID, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    search_query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
):
    pagination_params = Pagination(limit=limit, offset=offset)

    return await user_service.search_global_users(
        user_sid=current_user,
        search_query=search_query,
        pagination_params=pagination_params,
    )


@router.patch(path="/", response_model=UserResponse)
async def upload_user_avatar(
    current_user: Annotated[UUID, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    avatar: UploadFile = File(...),
):
    return await user_service.upload_user_avatar(
        user_sid=current_user,
        file=avatar,
    )
