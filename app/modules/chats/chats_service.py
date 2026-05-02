from typing import Annotated
from uuid import UUID

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.database import Chats, get_session
from app.modules.users.user_service import UserService, get_user_service

from .chats_repo import ChatsRepository
from .schemas import (
    ChatParticipantUser,
    FullChatInfo,
    GetChatResponse,
    GetChatsResponse,
    Pagination,
)


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

    async def create_personal_chat(
        self, current_user_sid: UUID, receiver_sid: UUID
    ) -> GetChatResponse:
        """Создание личного чата"""
        receiver = await self.user_service.get_user(
            user_sid=receiver_sid, as_model=True
        )
        if not receiver:
            raise BackendException(
                status_code=404,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
            )

        existing_chat = await self.chats_repo.find_personal_chat_between_users(
            self.session, current_user_sid, receiver_sid
        )
        if existing_chat:
            raise BackendException(
                result=ResultBase(code=CommonCodesEnum.CHAT_ALREADY_EXISTS),
                status_code=409,
            )

        current_user = await self.user_service.get_user(
            user_sid=current_user_sid, as_model=True
        )
        chat_name = f"{current_user.name} {current_user.surname} & {receiver.name} {receiver.surname}"

        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_name=chat_name,
                chat_type="personal",
                avatar=None,
            ),
        )
        await self.session.flush()

        await self.chats_repo.add_participant(
            self.session, current_user_sid, new_chat.sid, "admin"
        )
        await self.chats_repo.add_participant(
            self.session, receiver_sid, new_chat.sid, "admin"
        )

        await self.session.commit()

        return await self.get_chat_by_id(current_user_sid, new_chat.sid)

    async def create_group_chat(
        self, current_user_sid: UUID, chat_name: str
    ) -> GetChatResponse:
        """Создание группового чата"""
        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_name=chat_name,
                chat_type="group",
                avatar=None,
            ),
        )
        await self.session.flush()

        await self.chats_repo.add_participant(
            self.session, current_user_sid, new_chat.sid, "admin"
        )

        await self.session.commit()

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self.get_chat_by_id(current_user_sid, new_chat.sid),
        )

    async def _map_chat_to_info(
        self, chat: Chats, simplified: bool = False
    ) -> FullChatInfo:
        """Маппинг чата в ChatInfo DTO"""
        participants = []
        unread_count = 0

        for uc in chat.users_chats:
            participants.append(ChatParticipantUser.model_validate(uc))

        return FullChatInfo(
            sid=chat.sid,
            type=chat.chat_type,
            chatName=chat.chat_name,
            unread_count=unread_count,
            participants=participants if not simplified else [],
            is_pinned=False,
            is_muted=False,
            created_at=chat.created_at.isoformat() if chat.created_at else "",
            attachments=[],
        )

    async def get_chat_by_id(self, user_sid: UUID, chat_sid: UUID) -> GetChatResponse:
        """Получение полной информации о чате по ID"""
        chat = await self.chats_repo.get_chat_with_details(self.session, chat_sid)

        if not chat:
            raise BackendException(
                status_code=404, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )

        is_participant = any(
            str(uc.user_sid) == str(user_sid) and uc.left_at is None
            for uc in chat.users_chats
        )
        if not is_participant:
            raise BackendException(
                status_code=403,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
            )

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_info(chat, simplified=False),
        )

    async def get_user_chats(
        self, user_sid: UUID, skip: int = 0, limit: int = 50
    ) -> GetChatsResponse:
        """Получение всех чатов пользователя с пагинацией (упрощенный вид)"""
        # Используем новый метод репозитория для загрузки чатов и их зависимостей (избегаем N+1)
        chats, total = await self.chats_repo.get_filtered_with_details(
            self.session, user_sid, skip, limit
        )

        chat_infos = [
            await self._map_chat_to_info(chat, simplified=True) for chat in chats
        ]

        return GetChatsResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chats=chat_infos,
            pagination=Pagination(total=total, limit=limit, offset=skip),
        )

    async def delete_chat(self, chat_sid: UUID, current_user_sid: UUID) -> None:
        """Удаление группы (только админ может удалить)"""
        user_chat = await self.chats_repo.get_user_chat(
            self.session, chat_sid, current_user_sid
        )

        if not user_chat or user_chat.role != "admin":
            raise BackendException(
                status_code=403,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
            )

        chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
        if chat:
            # Сначала очищаем все связи пользователей с этим чатом,
            # чтобы избежать ошибки внешнего ключа (foreign key constraint)
            await self.chats_repo.remove_all_users_from_chat(self.session, chat_sid)
            # Затем удаляем сам чат
            await self.chats_repo.delete(self.session, chat)
            await self.session.commit()

    async def leave_or_clear_chat(self, chat_sid: UUID, current_user_sid: UUID) -> None:
        """Метод для удаления связи пользователя с чатом (выход из группы / очистка у себя)"""
        # Удаляем связь в UsersChats для текущего пользователя
        await self.chats_repo.remove_user_from_chat(
            self.session, chat_sid, current_user_sid
        )

        # Проверяем количество оставшихся участников
        participants_count = await self.chats_repo.count_chat_participants(
            self.session, chat_sid
        )

        # Если в чате никого не осталось, удаляем его полностью
        if participants_count == 0:
            chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
            if chat:
                await self.chats_repo.delete(self.session, chat)

        await self.session.commit()


async def get_chats_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ChatsService:
    chats_repo = ChatsRepository()

    return ChatsService(
        session=session,
        chats_repo=chats_repo,
        user_service=user_service,
    )
