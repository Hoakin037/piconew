from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BaseRepository
from app.database.tables import Files


class FilesRepo(BaseRepository[Files]):
    def __init__(self):
        super().__init__(Files)

    async def get_files_by_ids(
        self, files_sids: list[UUID], session: AsyncSession
    ) -> list[Files]:
        if not files_sids:
            return []

        query = select(Files).where(Files.sid.in_(files_sids))
        query = await session.execute(query)
        return query.scalars().all()


async def get_files_repo():
    return FilesRepo()
