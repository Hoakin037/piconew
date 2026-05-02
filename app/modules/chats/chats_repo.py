from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Chats, UsersChats
from app.database.base_repo import BaseRepository


class ChatsRepository(BaseRepository[Chats]):
    def __init__(self):
        super().__init__(Chats)

    async def add_participant(
        self,
        session: AsyncSession,
        user_sid: UUID,
        chat_sid: UUID,
        role: str = "member",
    ) -> UsersChats:
        user_chat = UsersChats(
            user_sid=user_sid, chat_sid=chat_sid, role=role, left_at=None
        )
        session.add(user_chat)
        await session.flush()
        return user_chat

    async def get_filtered(
        self,
        session: AsyncSession,
        user_sid: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Chats], int]:
        subquery = select(UsersChats.chat_sid).where(
            UsersChats.user_sid == user_sid, UsersChats.left_at.is_(None)
        )

        query = select(Chats).where(Chats.sid.in_(subquery))

        return await self._apply_pagination(query, session, skip, limit)
