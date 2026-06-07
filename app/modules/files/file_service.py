from typing import Annotated

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import UUID

from app.database import get_session
from app.database.tables import Files

from .files_repo import FilesRepo, get_files_repo
from .files_s3_repo import FilesS3Repository, get_files_s3_repo


class FilesService:
    def __init__(
        self,
        files_repo: FilesRepo,
        s3_files_repo: FilesS3Repository,
        session: AsyncSession,
    ):
        self.files_repo = files_repo
        self.s3_repo = s3_files_repo
        self.session = session

    async def create_file(self, file: UploadFile) -> Files:
        new_file = await self.files_repo.create(self.session, Files())
        url = self.s3_repo.put_temp_object(
            data=file.file.read(), url=f"files/{new_file.sid}"
        )
        new_file = await self.files_repo.update(self.session, new_file, {"url": url})
        await self.session.commit()
        await self.session.refresh(new_file)

        return new_file

    async def replace_file_from_temp(self, file_sid: UUID) -> Files:
        file = await self.files_repo.get_by_sid(self.session, file_sid)
        url = self.s3_repo.copy_object(source_url=file.url, new_url="/files/{file.sid}")
        new_file = await self.files_repo.update(self.session, file, {"url": url})
        await self.session.commit()
        await self.session.refresh(new_file)

        return new_file


async def get_file_service(
    files_repo: Annotated[FilesRepo, Depends(get_files_repo)],
    s3_repo: Annotated[FilesS3Repository, Depends(get_files_s3_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return FilesService(files_repo, s3_repo, session)
