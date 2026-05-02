from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.database.tables import Chats, UsersChats


class ChatsCustomOptions:
    @staticmethod
    def with_users_chats() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.users_chats),)

    @staticmethod
    def with_users_chats_and_users() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.users_chats).selectinload(UsersChats.users),)

    @staticmethod
    def with_messages() -> tuple[ExecutableOption, ...]:
        return (selectinload(Chats.chat_messages),)

    @staticmethod
    def with_all() -> tuple[ExecutableOption, ...]:
        return (
            selectinload(Chats.users_chats).selectinload(UsersChats.users),
            selectinload(Chats.chat_messages),
        )
