from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

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
):
    return await file_service.create_file(file)
