from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.core.jwt import get_current_user

from .file_service import FilesService, get_file_service
from .schemas import AttachmentBase

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    path="/upload_file",
    response_model=AttachmentBase,
)
async def upload_file(
    file_service: Annotated[FilesService, Depends(get_file_service)],
    file: UploadFile = File(...),
    current_user: UUID = Depends(get_current_user),
):
    return await file_service.create_file(file)
