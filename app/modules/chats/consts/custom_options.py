from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from database.tables import Chats, Messages


class ChatsCustomOptions(ExecutableOption):
    @staticmethod
    async def with_users_chats() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.users_chats),)

    @staticmethod
    async def with_messages() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.chat_messages),)
