import magic
from fastapi import UploadFile

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase

ALLOWED_AVATAR_MIMES = {
    "image/gif",
    "image/png",
    "image/jpg",
    "image/jpeg",
    "image/webp",
    "video/mp4",
}


def validate_mime(mime: str):
    if mime not in ALLOWED_AVATAR_MIMES:
        raise BackendException(
            status_code=400,
            result=ResultBase(code=CommonCodesEnum.INVALID_FILE_EXTENSION),
            detail=f"Недопустимый формат файла для аватарки/обоев. Разрешено: {ALLOWED_AVATAR_MIMES}",
        )


def get_mime_type_from_bytes(buffer: bytes) -> str:
    return magic.from_buffer(buffer, mime=True)


async def get_mime_type_from_upload_file(file: UploadFile) -> str:
    header = await file.read(2048)

    await file.seek(0)

    return magic.from_buffer(header, mime=True)


def get_mime_type_from_local_path(file_path: str) -> str:
    return magic.from_file(file_path, mime=True)
