from os.path import basename
from typing import Literal
from uuid import UUID

from pydantic import computed_field

from app.common.schemas import CoreSchema


class AttachmentBase(CoreSchema):
    sid: UUID
    url: str
    extension: str

    @computed_field
    @property
    def filename(self) -> str:
        return basename(self.url)


class FileInfo(CoreSchema):
    url: str
    extension: str


class ImageInfo(CoreSchema):
    url: str
    extension: str
    type: Literal["avatar", "wallpaper"]
