from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from socketio import AsyncServer
from starlette import status

from app.common import setup_logging
from app.common.core import JWTManager, get_jwt_config
from app.common.core.jwt import get_current_user
from app.common.core.sio import get_sio_server, sio
from app.modules.messages.utils import parse_jwt_token

from .message_service import MessagesService, get_messages_service
from .schemas import (
    GetMessagesResponse,
    MessageDeleteResponse,
    MessageEdit,
    MessageResponse,
    MessageSend,
    MessageSession,
)

logger = setup_logging(__name__)


router = APIRouter(prefix="", tags=["Messages"])


@sio.event
async def connect(sid, environ, auth: dict):
    token = parse_jwt_token(environ, auth)

    if not token:
        return False

    try:
        jwt_manager = JWTManager(get_jwt_config())
        user_sid = await jwt_manager.decode_token(token)

        await sio.save_session(
            sid,
            MessageSession(
                user_sid=str(user_sid),
                token=token,
                connected_at=datetime.now(UTC).isoformat(),
            ).model_dump(),
        )

        logger.info(f"User {user_sid} connected!")
        return True

    except Exception:
        return False


@sio.event
async def disconnect(sid: str):
    pass


@sio.on("join_chat")
async def handle_join(sid, chat_sid: dict):
    await sio.enter_room(sid, chat_sid["chat_sid"])
    await sio.emit(
        "system_msg", {"text": f"User {sid} joined"}, room=chat_sid["chat_sid"]
    )
    logger.info(f"User {sid} joined room {chat_sid['chat_sid']}")


@router.post(
    "/{chat_sid}/message",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    message_service: Annotated[MessagesService, Depends(get_messages_service)],
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    message_send: MessageSend,
    chat_sid: UUID = Path(...),
):
    new_message = await message_service.process_and_send_message(
        sender_sid=current_user,
        chat_sid=chat_sid,
        message_send=message_send,
    )

    message_dict = new_message.model_dump(mode="json")
    await sio_server.emit("new_message", message_dict, room=str(chat_sid))

    return new_message


@router.get("/{chat_sid}/messages", response_model=GetMessagesResponse, status_code=200)
async def get_chat_messages(
    current_user: Annotated[UUID, Depends(get_current_user)],
    messages_service: Annotated[MessagesService, Depends(get_messages_service)],
    chat_sid: UUID = Path(...),
    cursor_message_sid: UUID | None = Query(alias="cursorMessageSid", default=None),
    limit: int = Query(20, ge=1, le=100),
):
    return await messages_service.get_chat_messages(
        user_sid=current_user,
        chat_sid=chat_sid,
        cursor=cursor_message_sid,
        limit=limit,
    )


@router.get(
    path="/message/{message_sid}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
)
async def get_message(
    current_user: Annotated[UUID, Depends(get_current_user)],
    messages_service: Annotated[MessagesService, Depends(get_messages_service)],
    message_sid: UUID = Path(...),
):
    return await messages_service.get_message(
        message_sid=message_sid,
        user_sid=current_user,
    )


@router.patch(
    path="/message/{message_sid}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
)
async def edit_message(
    request: MessageEdit,
    current_user: Annotated[UUID, Depends(get_current_user)],
    messages_service: Annotated[MessagesService, Depends(get_messages_service)],
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    message_sid: UUID = Path(...),
):
    updated_message = await messages_service.edit_message(
        user_sid=current_user, message_sid=message_sid, content=request.content
    )

    # message_dict = updated_message.model_dump(mode="json")
    # await sio_server.emit("new_message", message_dict, room=str(updated_message.chat_sid))

    return updated_message


@router.delete(
    path="/message/{message_sid}",
    status_code=status.HTTP_200_OK,
    response_model=MessageDeleteResponse,
)
async def delete_message(
    current_user: Annotated[UUID, Depends(get_current_user)],
    messages_service: Annotated[MessagesService, Depends(get_messages_service)],
    sio_server: Annotated[AsyncServer, Depends(get_sio_server)],
    message_sid: UUID = Path(...),
):
    deleted_msg_sid, chat_sid = await messages_service.delete_message(
        user_sid=current_user, message_sid=message_sid
    )

    # await sio_server.emit(
    #     "delete_message",
    #     {"message_sid": str(deleted_msg_sid)},
    #     room=str(chat_sid)
    # )

    return MessageDeleteResponse(message_sid=deleted_msg_sid)
