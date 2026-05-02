from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base_repo import BaseRepository
from app.database.tables import Users


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


async def get_user_repo() -> UsersRepository:
    return UsersRepository()
