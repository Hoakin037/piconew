from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from app.common import setup_logging
from app.common.core import JWTManager, get_jwt_config
from app.common.core.jwt import get_current_user
from app.common.core.redis import get_redis_config, init_redis_client
from app.common.core.sio import sio
from app.database.db_init import db_manager
from app.modules.messages.message_service import MessagesService, get_messages_service
from app.modules.messages.postgres_repo import MessagesRepository
from app.modules.messages.redis_repo import MessagesRedisRepository
from app.modules.messages.schemas import GetMessagesResponse, MessageCreate
from app.modules.users.user_repo import UsersRepository

logger = setup_logging(__name__)


@sio.event
async def connect(sid, environ, auth: dict):
    token = None

    if auth and isinstance(auth, dict):
        token = auth.get("token") or auth.get("authorization")

    if not token and environ.get("QUERY_STRING"):
        import urllib.parse

        qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
        token_list = qs.get("token") or qs.get("authorization")
        if token_list:
            token = token_list[0]

    if not token:
        token = environ.get("HTTP_AUTHORIZATION") or environ.get("HTTP_TOKEN")
        if token and token.startswith("Bearer "):
            token = token[7:].strip()

    if not token:
        return False

    try:
        jwt_manager = JWTManager(get_jwt_config())
        user_sid = await jwt_manager.decode_token(token)

        await sio.save_session(
            sid,
            {
                "user_sid": str(user_sid),
                "token": token,
                "connected_at": datetime.now(UTC).isoformat(),
            },
        )

        logger.info(f"User {user_sid} connected!")
        return True

    except Exception:
        return False


@sio.event
async def disconnect(sid: str):
    pass


@sio.on("send_message")
async def handle_send_message(sid: str, data: dict):
    ws_session = await sio.get_session(sid)
    user_sid = ws_session.get("user_sid")

    if not user_sid:
        logger.warning(f"User {user_sid} not authenticated")
        await sio.emit("error", {"detail": "Not authenticated"}, to=sid)
        return None

    redis_client = init_redis_client(get_redis_config())

    async with db_manager.session_scope() as session:
        service = MessagesService(
            session=session,
            msg_repo=MessagesRepository(),
            user_repo=UsersRepository(),
            redis_repo=MessagesRedisRepository(redis_client),
        )

        try:
            message = MessageCreate(
                **data,
                sender_sid=user_sid,
            )
            response = await service.process_message(message)

            await sio.emit("new_message", response, room=str(data.get("chat_sid")))

            return {"status": "ok", "sid": str(response.get("sid"))}

        except Exception as e:
            await session.rollback()  # на всякий случай
            logger.info(f"Error in send_message: {e}")
            return {"status": "error", "detail": str(e)}
        finally:
            await redis_client.close()


@sio.on("join_chat")
async def handle_join(sid, chat_sid: dict):
    await sio.enter_room(sid, chat_sid["chat_sid"])
    await sio.emit(
        "system_msg", {"text": f"User {sid} joined"}, room=chat_sid["chat_sid"]
    )
    logger.info(f"User {sid} joined room {chat_sid['chat_sid']}")


messages_router = APIRouter(prefix="", tags=["Messages"])


@messages_router.get(
    "/{chat_sid}/messages", response_model=GetMessagesResponse, status_code=200
)
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
