from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Chats, BaseRepository


class ChatsRepository(BaseRepository[Chats]):
    pass
