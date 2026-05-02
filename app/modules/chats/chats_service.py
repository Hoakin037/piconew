from typing import Annotated
from uuid import UUID

from fastapi.params import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.database import Chats, UsersChats, get_session
from app.modules.users.user_service import UserService, get_user_service

from .chats_repo import ChatsRepository
from .schemas import (
    ChatInfo,
    ChatParticipantUser,
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
        # Проверяем, что получатель существует
        receiver = await self.user_service.get_user(
            user_sid=receiver_sid, as_model=True
        )
        if not receiver:
            raise BackendException(
                status_code=404,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
            )

        # Проверяем, не существует ли уже личный чат между этими пользователями
        existing_chat = await self._find_existing_personal_chat(
            current_user_sid, receiver_sid
        )
        if existing_chat:
            raise BackendException(
                result=ResultBase(code=CommonCodesEnum.CHAT_ALREADY_EXISTS),
                status_code=409,
            )

        # Создаем название чата из имен пользователей
        current_user = await self.user_service.get_user(
            user_sid=current_user_sid, as_model=True
        )
        chat_name = f"{current_user.name} {current_user.surname} & {receiver.name} {receiver.surname}"

        # Создаем новый чат
        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_name=chat_name,
                chat_type="personal",
                avatar=None,
            ),
        )
        await self.session.flush()

        # Добавляем участников
        await self.chats_repo.add_participant(
            self.session, current_user_sid, new_chat.sid, "admin"
        )
        await self.chats_repo.add_participant(
            self.session, receiver_sid, new_chat.sid, "admin"
        )

        await self.session.commit()

        # Возвращаем созданный чат
        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self.get_chat_by_id(current_user_sid, new_chat.sid),
        )

    async def create_group_chat(
        self, current_user_sid: UUID, chat_name: str
    ) -> GetChatResponse:
        """Создание группового чата"""
        # Создаем новый групповой чат
        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_name=chat_name,
                chat_type="group",
                avatar=None,
            ),
        )
        await self.session.flush()

        # Добавляем создателя как админа
        await self.chats_repo.add_participant(
            self.session, current_user_sid, new_chat.sid, "admin"
        )

        await self.session.commit()

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self.get_chat_by_id(current_user_sid, new_chat.sid),
        )

    async def _find_existing_personal_chat(
        self, user_sid_1: UUID, user_sid_2: UUID
    ) -> Chats | None:
        """Поиск существующего личного чата между двумя пользователями"""
        # Находим чаты, где оба пользователя являются участниками и тип чата 'personal'
        subquery = (
            select(UsersChats.chat_sid)
            .where(UsersChats.user_sid.in_([user_sid_1, user_sid_2]))
            .group_by(UsersChats.chat_sid)
            .having(func.count(UsersChats.user_sid) == 2)
        )

        query = (
            select(Chats)
            .where(Chats.sid.in_(subquery))
            .where(Chats.chat_type == "personal")
        )

        result = await self.session.execute(query)
        return result.scalars().first()

    async def _map_chat_to_info(
        self, chat: Chats, current_user_sid: UUID, simplified: bool = False
    ) -> ChatInfo:
        """Маппинг чата в ChatInfo DTO"""
        participants = []
        unread_count = 0

        for uc in chat.users_chats:
            u = uc.users

            participants.append(
                ChatParticipantUser(
                    sid=u.sid,
                    name=u.name,
                    surname=u.surname,
                    email=u.email,
                    username=u.username,
                    avatar=u.avatar,
                    status=u.status,
                    is_active=u.is_active,
                    created_at=u.created_at.isoformat()
                    if hasattr(u, "created_at")
                    else "",
                    role=uc.role,
                    joined_at=uc.joined_at.isoformat() if uc.joined_at else "",
                    left_at=uc.left_at.isoformat() if uc.left_at else None,
                )
            )

        return ChatInfo(
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

    async def get_chat_by_id(self, user_sid: UUID, chat_sid: UUID) -> ChatInfo:
        """Получение полной информации о чате по ID"""
        query = (
            select(Chats)
            .where(Chats.sid == chat_sid)
            .options(
                selectinload(Chats.users_chats).selectinload(UsersChats.users),
                selectinload(Chats.chat_messages),
            )
        )
        result = await self.session.execute(query)
        chat = result.scalars().first()

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

        return await self._map_chat_to_info(chat, user_sid, simplified=False)

    async def get_user_chats(
        self, user_sid: UUID, skip: int = 0, limit: int = 50
    ) -> GetChatsResponse:
        """Получение всех чатов пользователя с пагинацией (упрощенный вид)"""
        chats, total = await self.chats_repo.get_filtered(
            self.session, user_sid, skip, limit
        )

        # Загружаем участников и сообщения для каждого чата
        for chat in chats:
            await self.session.execute(
                select(Chats)
                .where(Chats.sid == chat.sid)
                .options(
                    selectinload(Chats.users_chats).selectinload(UsersChats.users),
                    selectinload(Chats.chat_messages),
                )
            )

        chat_infos = []
        for chat in chats:
            chat_infos.append(
                await self._map_chat_to_info(chat, user_sid, simplified=True)
            )

        return GetChatsResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chats=chat_infos,
            pagination=Pagination(total=total, limit=limit, offset=skip),
        )

    async def delete_chat(self, chat_sid: UUID, current_user_sid: UUID) -> None:
        """Удаление группы (только админ может удалить)"""
        # Проверяем, является ли пользователь админом чата
        query = select(UsersChats).where(
            UsersChats.chat_sid == chat_sid,
            UsersChats.user_sid == current_user_sid,
            UsersChats.left_at.is_(None),
        )
        result = await self.session.execute(query)
        user_chat = result.scalars().first()

        if not user_chat or user_chat.role != "admin":
            raise BackendException(
                status_code=403,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
            )

        chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
        if chat:
            await self.chats_repo.delete(self.session, chat)
            await self.session.commit()

    async def update_chat_settings(
        self,
        chat_sid: UUID,
        current_user_sid: UUID,
        chat_name: str = None,
        avatar: str = None,
        is_pinned: bool = None,
        is_muted: bool = None,
    ) -> None:
        query = select(UsersChats).where(
            UsersChats.chat_sid == chat_sid,
            UsersChats.user_sid == current_user_sid,
            UsersChats.left_at.is_(None),
        )
        result = await self.session.execute(query)
        user_chat = result.scalars().first()

        if not user_chat:
            raise BackendException(
                status_code=403,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
            )

        # Обновляем настройки чата (только админ может менять имя и аватар)
        chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
        if chat:
            if chat_name is not None and user_chat.role == "admin":
                chat.chat_name = chat_name
            if avatar is not None and user_chat.role == "admin":
                chat.avatar = avatar

        # Обновляем личные настройки пользователя
        if is_pinned is not None:
            user_chat.is_pinned = is_pinned
        if is_muted is not None:
            user_chat.is_muted = is_muted

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
