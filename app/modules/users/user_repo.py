from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import  select

from app.database.tables import Users

class UsersRepository:

    async def get_user_by_sid(self, user_sid: UUID, session: AsyncSession) -> Users | None:
        query = select(Users).where(Users.sid==user_sid)
        result = await session.execute(query)

        return result.scalars().first()

    async def get_user_by_username(self, username: str, session: AsyncSession) -> Users | None:
        query = select(Users).where(Users.username==username)
        result = await session.execute(query)

        return result.scalars().first()

    async def get_user_by_email(self, email: str, session: AsyncSession) -> Users | None:
        query = select(Users).where(Users.email==email)
        result = await session.execute(query)

        return result.scalars().first()

    async def create_user(self, user: Users, session: AsyncSession) -> None:
        session.add(user)

    async def delete_user(self, user: Users, session: AsyncSession) -> None:
        await session.delete(user)


async def get_user_repo() -> UsersRepository:
    return UsersRepository()