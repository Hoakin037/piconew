from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from socketio import AsyncServer

from app.common.consts import CommonCodesEnum
from app.common.core.jwt import get_current_user
from app.common.core.sio import get_sio_server
from app.common.schemas import Pagination, ResultBase
from app.modules.users import UserService, get_user_service
from app.modules.users.schemas import GetUsersResponse

from .chats_service import ChatsService, get_chats_service
from .schemas import (
    AddGroupMembers,
    BaseResponse,
    CreateChatRequest,
    CreateGroupRequest,
    GetChatResponse,
    GetChatsResponse,
)

chats = APIRouter(prefix="/chats", tags=["Chats"])


@chats.post("/create_chat", status_code=201, response_model=GetChatResponse)
async def create_chat(
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    request: CreateChatRequest,
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    user_chat, other_chat = await chats_service.create_personal_chat(
        current_user, request.receiver_id
    )
    await sio_server.emit(
        "new_chat", user_chat.model_dump(mode="json"), room=str(current_user)
    )
    await sio_server.emit(
        "new_chat", other_chat.model_dump(mode="json"), room=str(request.receiver_id)
    )

    return user_chat


@chats.post("/create_group", status_code=201, response_model=GetChatResponse)
async def create_group(
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    request: CreateGroupRequest,
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    group = await chats_service.create_group_chat(current_user, request)
    await sio_server.emit(
        "new_chat", group.model_dump(mode="json"), room=str(current_user)
    )
    for user_sid in request.members:
        await sio_server.emit(
            "new_chat", group.model_dump(mode="json"), room=str(user_sid)
        )

    return group


@chats.get("/", response_model=GetChatsResponse)
async def get_user_chats(
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await chats_service.get_user_chats(
        user_sid=current_user,
        skip=offset,
        limit=limit,
    )


@chats.get("/{chat_sid}", response_model=GetChatResponse)
async def get_chat_by_id(
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    return await chats_service.get_chat_by_id(current_user, chat_sid)


@chats.delete("/{chat_sid}", response_model=BaseResponse)
async def delete_chat(
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    await chats_service.delete_chat(chat_sid, current_user)
    return BaseResponse(result=ResultBase(code=CommonCodesEnum.DEFAULT))


@chats.delete("/{chat_sid}/leave", response_model=BaseResponse)
async def leave_chat(
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    """
    Удаление чата/группы у себя (выход из чата).
    Если пользователь был последним участником, чат полностью удаляется.
    """
    await chats_service.leave_or_clear_chat(chat_sid, current_user)
    return BaseResponse(result=ResultBase(code=CommonCodesEnum.DEFAULT))


@chats.get("/{chat_sid}/users", response_model=GetUsersResponse)
async def search_users_for_chat(
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    search_query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
):
    pagination_params = Pagination(limit=limit, offset=offset)

    return await user_service.search_users_for_chat(
        user_sid=current_user,
        chat_sid=chat_sid,
        search_query=search_query,
        pagination_params=pagination_params,
    )


@chats.patch("/{chat_sid}/set_avatar", response_model=GetChatResponse)
async def set_group_avatar(
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    file: UploadFile = File(...),
    chats_service: ChatsService = Depends(get_chats_service),
):
    chat = await chats_service.set_group_avatar(chat_sid, file, current_user)

    await sio_server.emit(
        "update_chat", chat.model_dump(mode="json"), room=str(current_user)
    )

    return chat


@chats.patch("/{chat_sid}/set_wallpaper", response_model=GetChatResponse)
async def set_wallpaper(
    chat_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    file: UploadFile = File(...),
    chats_service: ChatsService = Depends(get_chats_service),
):
    return await chats_service.set_wallpaper(chat_sid, file, current_user)


@chats.post(path="/{group_sid}/add_members", response_model=GetChatResponse)
async def add_group_members(
    members: AddGroupMembers,
    group_sid: UUID = Path(),
    current_user: UUID = Depends(get_current_user),
    chats_service: ChatsService = Depends(get_chats_service),
):
    return await chats_service.add_group_members(
        group_sid, current_user, members.members
    )
