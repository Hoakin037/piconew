from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from app.database import Chats, UsersChats
from app.database.base_repo import BaseRepository
from app.modules.chats.consts.custom_options import ChatsCustomOptions


class ChatsRepository(BaseRepository[Chats]):
    def __init__(self):
        super().__init__(Chats)

    async def add_participant(
        self,
        session: AsyncSession,
        user_sid: UUID,
        chat_sid: UUID,
        avatar: str | None,
        chat_name: str,
        role: str = "member",
    ) -> UsersChats:
        user_chat = UsersChats(
            user_sid=user_sid,
            chat_sid=chat_sid,
            role=role,
            left_at=None,
            avatar=avatar,
            chat_name=chat_name,
        )
        session.add(user_chat)
        await session.flush()
        return user_chat

    async def get_user_chat(
        self, session: AsyncSession, chat_sid: UUID, user_sid: UUID
    ) -> UsersChats | None:
        query = select(UsersChats).where(
            UsersChats.chat_sid == chat_sid,
            UsersChats.user_sid == user_sid,
            UsersChats.left_at.is_(None),
        )
        result = await session.execute(query)
        return result.scalars().first()

    async def remove_user_from_chat(
        self, session: AsyncSession, chat_sid: UUID, user_sid: UUID
    ) -> None:
        user_chat = await self.get_user_chat(session, chat_sid, user_sid)
        if user_chat:
            await session.delete(user_chat)
            await session.flush()

    async def get_filtered_with_details(
        self,
        session: AsyncSession,
        user_sid: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Chats], int]:
        subquery = select(UsersChats.chat_sid).where(
            UsersChats.user_sid == user_sid, UsersChats.left_at.is_(None)
        )

        query = (
            select(Chats)
            .where(Chats.sid.in_(subquery))
            .options(*ChatsCustomOptions.with_users_chats_and_users())
        )

        return await self._apply_pagination(query, session, skip, limit)

    async def find_personal_chat_between_users(
        self, session: AsyncSession, user_sid_1: UUID, user_sid_2: UUID
    ) -> Chats | None:
        subquery = (
            select(UsersChats.chat_sid)
            .where(UsersChats.user_sid.in_([user_sid_1, user_sid_2]))
            .group_by(UsersChats.chat_sid)
            .having(func.count(UsersChats.user_sid) == 2)
        )

        query = (
            select(Chats)
            .where(Chats.sid.in_(subquery))
            .where(Chats.chat_type == "personal")
        )
        result = await session.execute(query)
        return result.scalars().first()

    async def get_chat_with_options(
        self,
        session: AsyncSession,
        chat_sid: UUID,
        options: tuple[ExecutableOption, ...],
    ) -> Chats | None:
        query = select(Chats).where(Chats.sid == chat_sid).options(*options)
        result = await session.execute(query)
        return result.scalars().first()

    async def get_chat_with_details(
        self, session: AsyncSession, chat_sid: UUID
    ) -> Chats | None:
        return await self.get_chat_with_options(
            session, chat_sid, ChatsCustomOptions.with_all()
        )

    async def remove_all_users_from_chat(
        self, session: AsyncSession, chat_sid: UUID
    ) -> None:
        query = select(UsersChats).where(UsersChats.chat_sid == chat_sid)
        result = await session.execute(query)
        users_chats = result.scalars().all()
        for uc in users_chats:
            await session.delete(uc)
        await session.flush()

    async def count_chat_participants(
        self, session: AsyncSession, chat_sid: UUID
    ) -> int:
        query = (
            select(func.count())
            .select_from(UsersChats)
            .where(UsersChats.chat_sid == chat_sid)
        )
        return await session.scalar(query) or 0

    async def check_if_user_admin(
        self, chat_sid: UUID, user_sid: UUID, session: AsyncSession
    ) -> bool:
        query = select(UsersChats.role).where(
            UsersChats.chat_sid == chat_sid, UsersChats.user_sid == user_sid
        )
        result = await session.execute(query)
        result = result.scalars().first()
        return result == "admin"


async def get_chats_repo():
    return ChatsRepository()
