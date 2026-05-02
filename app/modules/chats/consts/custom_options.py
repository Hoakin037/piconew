from database.tables import Chats
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption


class ChatsCustomOptions(ExecutableOption):
    @staticmethod
    async def with_users_chats() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.users_chats),)

    @staticmethod
    async def with_messages() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.chat_messages),)
