from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base_repo import BaseRepository
from app.database.tables import Messages, UsersChats


class MessagesRepository(BaseRepository[Messages]):
    def __init__(self):
        super().__init__(Messages)

    async def save_message(self, session: AsyncSession, data: dict):
        stmt = (
            insert(Messages)
            .values(
                sid=UUID(data["sid"]),
                sender_sid=UUID(data["user"]["sid"]),
                chat_sid=UUID(data["chat_sid"]),
                content=data["content"],
                reply_message_sid=data.get("reply_to"),
                created_at=datetime.fromisoformat(data["created_at"]),
            )
            .on_conflict_do_nothing(index_elements=["sid"])
        )

        await session.execute(stmt)

    async def check_user_membership(
        self, session: AsyncSession, user_sid: UUID, chat_sid: UUID
    ) -> bool:
        query = select(
            exists().where(
                UsersChats.user_sid == user_sid, UsersChats.chat_sid == chat_sid
            )
        )
        res = await session.execute(query)

        return res.scalar() or False
