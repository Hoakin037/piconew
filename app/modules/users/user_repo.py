from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base_repo import BaseRepository
from app.database.tables import Users, UsersChats


class UsersRepository(BaseRepository[Users]):
    def __init__(self):
        super().__init__(Users)

    async def get_user_by_username(
        self, username: str, session: AsyncSession
    ) -> Users | None:
        query = select(Users).where(Users.username == username)
        result = await session.execute(query)

        return result.scalars().first()

    async def get_user_by_email(
        self, email: str, session: AsyncSession
    ) -> Users | None:
        query = select(Users).where(Users.email == email)
        result = await session.execute(query)

        return result.scalars().first()

    async def delete(self, user: Users, session: AsyncSession) -> None:
        await session.delete(user)

    async def search_users(
        self,
        session: AsyncSession,
        current_user_sid: UUID,
        search_query: str | None,
        skip: int,
        limit: int,
    ) -> tuple[Sequence[Users], int]:
        query = select(Users).where(Users.sid != current_user_sid)

        if search_query:
            search_term = f"%{search_query}%"
            query = query.where(
                or_(
                    Users.username.ilike(search_term),
                    Users.name.ilike(search_term),
                    Users.surname.ilike(search_term),
                )
            )

        return await self._apply_pagination(query, session, skip=skip, limit=limit)

    async def search_users_for_chat(
        self,
        session: AsyncSession,
        current_user_sid: UUID,
        chat_sid: UUID,
        search_query: str | None,
        skip: int,
        limit: int,
    ) -> tuple[Sequence[Users], int]:
        subquery = select(UsersChats.user_sid).where(
            UsersChats.chat_sid == chat_sid, UsersChats.left_at.is_(None)
        )

        query = select(Users).where(
            Users.sid != current_user_sid, Users.sid.not_in(subquery)
        )

        if search_query:
            search_term = f"%{search_query}%"
            query = query.where(
                or_(
                    Users.name.ilike(search_term),
                    Users.surname.ilike(search_term),
                )
            )

        return await self._apply_pagination(query, session, skip=skip, limit=limit)


async def get_user_repo() -> UsersRepository:
    return UsersRepository()
