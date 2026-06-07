from app.database import BaseRepository
from app.database.tables import Files


class FilesRepo(BaseRepository[Files]):
    def __init__(self):
        super().__init__(Files)


async def get_files_repo():
    return FilesRepo()
