from typing import Annotated, Literal

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import UUID

from app.database import get_session
from app.database.tables import Files

from . import AttachmentBase
from .files_repo import FilesRepo, get_files_repo
from .files_s3_repo import FilesS3Repository, get_files_s3_repo
from .schemas import FileInfo, ImageInfo
from .utils import get_mime_type_from_bytes, validate_mime


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

    async def upload_file(
        self, file: UploadFile, type: Literal["chat", "user"], sid: UUID
    ) -> str:
        return await self.s3_repo.put_object(
            data=file.file.read(), url=f"{type}/{sid}/{file.filename}"
        )

    async def get_img_file(self, sid: UUID | None):
        if not sid:
            return None

        file = await self.files_repo.get_by_sid(self.session, sid)

        if file:
            return FileInfo.model_validate(file)

        return None

    async def create_file(self, file: UploadFile, temp=True) -> AttachmentBase:
        new_file = await self.files_repo.create(self.session, Files())
        await self.session.flush()
        filename = file.filename
        file_data = file.file.read()
        extension = get_mime_type_from_bytes(file_data)

        url = (
            await self.s3_repo.put_temp_object(
                data=file_data, url=f"files/{new_file.sid}/{filename}"
            )
            if temp
            else await self.s3_repo.put_object(
                data=file_data, url=f"files/{new_file.sid}/{filename}"
            )
        )
        new_file = await self.files_repo.update(
            self.session, new_file, {"url": url, "extension": extension}
        )

        await self.session.commit()
        await self.session.refresh(new_file)

        return AttachmentBase.model_validate(new_file)

    async def create_img_file(
        self,
        file: UploadFile,
        sid: UUID,
        type: Literal["avatar", "wallpaper"],
        temp=True,
    ) -> ImageInfo:
        filename = file.filename
        file_data = file.file.read()
        extension = get_mime_type_from_bytes(file_data)
        validate_mime(extension)

        url = (
            await self.s3_repo.put_temp_object(
                data=file_data, url=f"files/{sid}/{filename}"
            )
            if temp
            else await self.s3_repo.put_object(
                data=file_data, url=f"files/{sid}/{filename}"
            )
        )

        return ImageInfo(
            url=url,
            extension=extension,
            type=type,
        )

    async def replace_file_from_temp(self, file_sid: UUID) -> Files:
        file = await self.files_repo.get_by_sid(self.session, file_sid)
        file_dto = AttachmentBase.model_validate(file)

        url = await self.s3_repo.copy_object(
            source_url=file_dto.url, new_url=f"files/{file_dto.sid}/{file_dto.filename}"
        )

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
