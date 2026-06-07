from database import BaseRepository
from database.tables import Files


class FilesRepo(BaseRepository[Files]):
    def __init__(self):
        super().__init__(Files)
