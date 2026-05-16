import asyncio
from datetime import UTC, datetime

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from uuid6 import uuid7

from app.common import setup_logging
from app.common.consts import CommonCodesEnum
from app.common.core.redis import get_redis_manager
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.database.db_init import db_manager, get_session
from app.modules.messages.postgres_repo import MessagesRepository
from app.modules.messages.redis_repo import MessagesRedisRepository
from app.modules.messages.schemas import MessageCreate
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

    async def process_message(self, message: MessageCreate) -> dict:
        if not await self.msg_repo.check_user_membership(
            self.session, message.sender_sid, message.chat_sid
        ):
            raise BackendException(
                status_code=status.HTTP_403_FORBIDDEN,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                detail="Вы не являетесь участником чата",
            )

        user = await self.user_repo.get_by_sid(self.session, message.sender_sid)
        if not user:
            raise BackendException(
                status_code=status.HTTP_404_NOT_FOUND,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
                detail="Пользователь не найден",
            )

        message.sid = uuid7()
        now = datetime.now(UTC)

        message_packet = {
            "sid": str(message.sid),
            "chat_sid": str(message.chat_sid),
            "content": message.content,
            "attachments": message.attachments,
            "reply_to": message.reply_message_sid,
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

        await self.redis_repo.cache_message(message.chat_sid, message_packet)

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
