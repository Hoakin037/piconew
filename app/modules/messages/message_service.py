import asyncio
from datetime import UTC, datetime
from uuid import UUID

from consts import CommonCodesEnum
from errors import BackendException
from fastapi import Depends, status
from schemas import ResultBase
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from uuid6 import uuid7

from app.common import setup_logging
from app.common.core.redis import get_redis_manager
from app.database.db_init import db_manager, get_session
from app.modules.messages.postgres_repo import MessagesRepository
from app.modules.messages.redis_repo import MessagesRedisRepository
from app.modules.users.user_repo import UsersRepository

logger = setup_logging(__name__)


class MessagesService:
    def __init__(
        self,
        session: AsyncSession,
        msg_repo: MessagesRepository,
        user_repo: UsersRepository,
        redis_repo: MessagesRedisRepository,
    ):
        self.session = session
        self.msg_repo = msg_repo
        self.user_repo = user_repo
        self.redis_repo = redis_repo

    async def process_message(self, data: dict) -> dict:
        sender_sid = UUID(str(data["sender_sid"]))
        chat_sid = UUID(str(data["chat_sid"]))

        if not await self.msg_repo.check_user_membership(
            self.session, sender_sid, chat_sid
        ):
            raise BackendException(
                status_code=status.HTTP_403_FORBIDDEN,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                detail="Вы не являетесь участником чата",
            )

        user = await self.user_repo.get_by_sid(self.session, sender_sid)
        if not user:
            raise BackendException(
                status_code=status.HTTP_404_NOT_FOUND,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
                detail="Пользователь не найден",
            )

        msg_sid = uuid7()
        now = datetime.now(UTC)

        message_packet = {
            "sid": str(msg_sid),
            "chat_sid": str(chat_sid),
            "content": data["content"],
            "attachments": data.get("attachments", []),
            "reply_to": data.get("reply_to"),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "user": {
                "sid": str(user.sid),
                "name": user.name,
                "surname": user.surname,
                "username": user.username,
                "avatar": user.avatar or None,
            },
        }

        await self.redis_repo.cache_message(chat_sid, message_packet)

        asyncio.create_task(self._bg_save(message_packet))

        return message_packet

    async def _bg_save(self, data: dict):
        async with db_manager.session_scope() as session:
            try:
                await self.msg_repo.save_message(session, data)
                await session.commit()
                logger.info(f"Сообщение {data['sid']} сохранено в БД")
            except Exception as e:
                await session.rollback()
                logger.info(f"Ошибка сохранения сообщения {data.get('sid')}: {e}")


async def get_messages_service(
    session: AsyncSession = Depends(get_session), redis_mgr=Depends(get_redis_manager)
):
    return MessagesService(
        session,
        MessagesRepository(),
        UsersRepository(),
        MessagesRedisRepository(redis_mgr.client),
    )
