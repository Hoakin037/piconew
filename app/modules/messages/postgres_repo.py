from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.base_repo import BaseRepository
from app.database.tables import Messages, UsersChats

from .schemas import MessageCreate


class MessagesRepository(BaseRepository[Messages]):
    def __init__(self):
        super().__init__(Messages)

    async def create_message(
        self, session: AsyncSession, message_create: MessageCreate
    ) -> Messages:
        message = Messages(
            sid=message_create.sid,
            sender_sid=message_create.sender_sid,
            chat_sid=message_create.chat_sid,
            content=message_create.content,
            reply_message_sid=message_create.reply_message_sid,
            created_at=message_create.created_at or datetime.utcnow(),
        )

        await self.create(session, message)
        await session.flush()
        await session.refresh(message, ["user"])
        return message

    async def check_user_membership(
        self, session: AsyncSession, user_sid: UUID, chat_sid: UUID
    ) -> bool:
        query = select(
            exists().where(
                UsersChats.user_sid == user_sid,
                UsersChats.chat_sid == chat_sid,
                UsersChats.left_at.is_(None),
            )
        )
        result = await session.execute(query)
        return result.scalar() or False

    async def get_messages_by_cursor(
        self, session: AsyncSession, chat_sid: UUID, cursor: UUID | None, limit: int
    ) -> tuple[Sequence[Messages], int]:
        messages_query = select(Messages).where(
            Messages.chat_sid == chat_sid, Messages.is_deleted == False
        )

        if cursor:
            messages_query = messages_query.where(Messages.sid < cursor)

        messages_query = (
            messages_query.order_by(Messages.sid.desc())
            .limit(limit)
            .options(selectinload(Messages.user))
        )

        count_query = (
            select(func.count())
            .select_from(Messages)
            .where(Messages.chat_sid == chat_sid, Messages.is_deleted == False)
        )

        messages_result = await session.execute(messages_query)
        count_result = await session.execute(count_query)

        return messages_result.scalars().all(), count_result.scalar_one() or 0

    async def get_last_message_in_chat(
        self, session: AsyncSession, chat_sid: UUID
    ) -> Messages | None:
        """Получить последнее сообщение в чате по chat_sid."""
        query = (
            select(Messages)
            .where(Messages.chat_sid == chat_sid, Messages.is_deleted == False)
            .order_by(Messages.created_at.desc(), Messages.sid.desc())
            .limit(1)
            .options(selectinload(Messages.user))
        )
        result = await session.execute(query)
        return result.scalars().first()


async def get_msg_repo():
    return MessagesRepository()
