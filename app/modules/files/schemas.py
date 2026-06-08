from os.path import basename
from pathlib import Path
from uuid import UUID

from pydantic import computed_field

from app.common.schemas import CoreSchema


class AttachmentBase(CoreSchema):
    sid: UUID
    url: str

    @computed_field
    @property
    def filename(self) -> str:
        return basename(self.url)

    @computed_field
    @property
    def extension(self) -> str:
        filename = self.filename
        return Path(filename).suffix
