from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from uuid6 import uuid7

from app.common import setup_logging
from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.common.schemas.pagination import CursorPagination
from app.database.db_init import get_session
from app.modules.chats.chats_repo import ChatsRepository, get_chats_repo
from app.modules.users.schemas import UserMessage
from app.modules.users.user_repo import UsersRepository, get_user_repo

from .options import MessagesCustomOptions
from .postgres_repo import MessagesRepository, get_msg_repo
from .redis_repo import MessagesRedisRepository, get_redis_repo
from .schemas import (
    GetMessagesResponse,
    MessageCreate,
    MessageResponse,
    MessageSend,
)

logger = setup_logging(__name__)


class MessagesService:
    def __init__(
        self,
        session: AsyncSession,
        msg_repo: MessagesRepository,
        user_repo: UsersRepository,
        redis_repo: MessagesRedisRepository,
        chats_repo: ChatsRepository,
    ):
        self.session = session
        self.msg_repo = msg_repo
        self.user_repo = user_repo
        self.redis_repo = redis_repo
        self.chats_repo = chats_repo

    async def _validate_chat_and_membership(self, user_sid: UUID, chat_sid: UUID):
        chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
        if not chat:
            raise BackendException(
                status_code=status.HTTP_404_NOT_FOUND,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
                detail="Чат не найден",
            )

        is_member = await self.msg_repo.check_user_membership(
            self.session, user_sid, chat_sid
        )
        if not is_member:
            raise BackendException(
                status_code=status.HTTP_403_FORBIDDEN,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                detail="Вы не являетесь участником чата",
            )

    async def process_and_send_message(
        self, sender_sid: UUID, chat_sid: UUID, message_send: MessageSend
    ) -> MessageResponse:
        await self._validate_chat_and_membership(sender_sid, chat_sid)

        message_create = MessageCreate(
            sid=uuid7(),
            chat_sid=chat_sid,
            sender_sid=sender_sid,
            content=message_send.content,
            attachments=message_send.attachments,
            reply_message_sid=message_send.reply_to,
            created_at=datetime.now(UTC),
        )

        new_message_db = await self.msg_repo.create_message(
            self.session, message_create
        )
        await self.session.commit()
        user_info = await self.user_repo.get_by_sid(
            self.session, new_message_db.user.sid
        )

        message = MessageResponse.model_validate(new_message_db)

        message.user = UserMessage(
            sid=new_message_db.user.sid,
            name=user_info.name,
            surname=user_info.surname,
            username=user_info.username,
        )

        await self.redis_repo.cache_message(chat_sid, message.model_dump(mode="json"))

        return message

    async def get_chat_messages(
        self, user_sid: UUID, chat_sid: UUID, cursor: UUID | None, limit: int
    ) -> GetMessagesResponse:
        chat_exists = await self.chats_repo.get_by_sid(self.session, chat_sid)
        if not chat_exists:
            raise BackendException(
                status_code=status.HTTP_404_NOT_FOUND,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
                detail="Чат не найден",
            )

        if not await self.msg_repo.check_user_membership(
            self.session, user_sid, chat_sid
        ):
            raise BackendException(
                status_code=status.HTTP_403_FORBIDDEN,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                detail="Вы не являетесь участником чата",
            )

        messages, total_count = await self.msg_repo.get_messages_by_cursor(
            self.session, chat_sid, cursor, limit + 1
        )

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        items = [MessageResponse.model_validate(message) for message in messages]

        return GetMessagesResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            items=items,
            pagination=CursorPagination(
                total=total_count, limit=limit, has_more=has_more
            ),
        )

    async def get_message(
        self,
        user_sid: UUID,
        message_sid: UUID,
    ):
        message = await self.msg_repo.get_by_sid(
            self.session,
            message_sid,
            custom_options=(*MessagesCustomOptions.with_user(),),
        )

        if not message:
            raise BackendException(
                status_code=status.HTTP_404_NOT_FOUND,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
                detail="Сообщение не найдено",
            )

        if not await self.msg_repo.check_user_membership(
            self.session, user_sid, message.chat_sid
        ):
            raise BackendException(
                status_code=status.HTTP_403_FORBIDDEN,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                detail="Вы не являетесь участником чата",
            )

        return MessageResponse.model_validate(message)


async def get_messages_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    msg_repo: Annotated[MessagesRepository, Depends(get_msg_repo)],
    user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
    redis_repo: Annotated[MessagesRedisRepository, Depends(get_redis_repo)],
    chats_repo: Annotated[ChatsRepository, Depends(get_chats_repo)],
) -> MessagesService:
    return MessagesService(
        session=session,
        msg_repo=msg_repo,
        user_repo=user_repo,
        redis_repo=redis_repo,
        chats_repo=chats_repo,
    )
