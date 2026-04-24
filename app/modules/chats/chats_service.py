from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Chats, Users, UsersChats
from app.modules.users.user_service import UserService
from .chats_repo import ChatsRepository

from .schemas import ChatsResponse, ChatsCreate, ChatsBase


class ChatsService:
    def __init__(
        self,
        session: AsyncSession,
        chats_repo: ChatsRepository,
        user_service: UserService,
    ):
        self.session = session
        self.chats_repo = chats_repo
        self.user_service = user_service

    async def create_users_chats(
        self,
        user_sid: UUID,
        chat_sid: UUID
    ):

    async def create_chat(
            self,
            chat: ChatsCreate,
    ):
        user = await self.user_service.get_user(user_sid=chat.user_sid)
        receiver = await self.user_service.get_user(user_sid=chat.receiver_sid)

        new_chat = self.chats_repo.create(
            obj=Chats(
                chat_name=chat.chat_name,
                chat_type=chat.chat_type,
                avatar=chat.avatar
            ),
            session=self.session,
        )
        await self.session.commit()
        await self.session.refresh(new_chat)


    async def get_chat(self, chats_sid: UUID) -> ChatsResponse:
        pass