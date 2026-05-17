from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.database.tables import Messages


class MessagesCustomOptions:
    @staticmethod
    def with_user() -> tuple[ExecutableOption]:
        return (selectinload(Messages.user),)
