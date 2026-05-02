from random import choice
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
from .consts.custom_options import ChatsCustomOptions
from .schemas import (
    ChatParticipantUser,
    FullChatInfo,
    GetChatResponse,
    GetChatsResponse,
    Pagination,
    ShortChatInfo,
)

avatars = [
    "https://static.wikia.nocookie.net/mems/images/b/b3/%D0%9E%D0%BA%D0%B0%D0%BA.webp/revision/latest/scale-to-width-down/1200?cb=20260102083423&path-prefix=ru",
    "https://spbcult.ru/upload/iblock/7b9/9n0tc4etzlpw3t1h1021gjzhwl226j5k.jpg",
    "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg",
    "https://i.pinimg.com/originals/6f/b7/26/6fb726d46f5894ed0c67399b8b42f4c0.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRAoIwxxUyWwjjPlHfFOG7_vXwn19Muf8B8QA&s",
    None,
]

avatars = [
    "https://static.wikia.nocookie.net/mems/images/b/b3/%D0%9E%D0%BA%D0%B0%D0%BA.webp/revision/latest/scale-to-width-down/1200?cb=20260102083423&path-prefix=ru",
    "https://spbcult.ru/upload/iblock/7b9/9n0tc4etzlpw3t1h1021gjzhwl226j5k.jpg",
    "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg",
    "https://i.pinimg.com/originals/6f/b7/26/6fb726d46f5894ed0c67399b8b42f4c0.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRAoIwxxUyWwjjPlHfFOG7_vXwn19Muf8B8QA&s",
    None,
]


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

        # После создания получаем полную информацию через get_chat_by_id (он использует get_chat_with_details)
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

        # Перезагружаем чат с подгрузкой всех связей
        chat_with_details = await self.chats_repo.get_chat_with_options(
            self.session, new_chat.sid, ChatsCustomOptions.with_all()
        )
        if not chat_with_details:
            raise BackendException(
                status_code=404, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_full_info(chat_with_details, current_user_sid),
        )

    @staticmethod
    async def _map_chat_to_short_info(
        chat: Chats, current_user_sid: UUID
    ) -> ShortChatInfo:
        """Маппинг чата в ShortChatInfo DTO (для списка чатов)"""
        user_chat = None
        for uc in chat.users_chats:
            if str(uc.user_sid) == str(current_user_sid):
                user_chat = uc
                break

        return ShortChatInfo(
            sid=chat.sid,
            type=chat.chat_type,
            chatName=chat.chat_name,
            avatar=chat.avatar or choice(avatars),
            unread_count=0,
            is_pinned=user_chat.is_pinned if user_chat else False,
            is_muted=user_chat.is_muted if user_chat else False,
            created_at=chat.created_at.isoformat() if chat.created_at else "",
        )

    @staticmethod
    async def _map_chat_to_full_info(
        chat: Chats, current_user_sid: UUID
    ) -> FullChatInfo:
        """Маппинг чата в FullChatInfo DTO (для конкретного чата)"""
        participants = []
        user_chat = None

        for uc in chat.users_chats:
            if str(uc.user_sid) == str(current_user_sid):
                user_chat = uc
            participants.append(ChatParticipantUser.model_validate(uc))

        return FullChatInfo(
            sid=chat.sid,
            type=chat.chat_type,
            chatName=chat.chat_name,
            avatar=chat.avatar or choice(avatars),
            unread_count=0,
            participants=participants,
            is_pinned=user_chat.is_pinned if user_chat else False,
            is_muted=user_chat.is_muted if user_chat else False,
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
            chat=await self._map_chat_to_full_info(chat, user_sid),
        )

    async def get_user_chats(
        self, user_sid: UUID, skip: int = 0, limit: int = 50
    ) -> GetChatsResponse:
        """Получение всех чатов пользователя с пагинацией (упрощенный вид)"""
        chats, total = await self.chats_repo.get_filtered_with_details(
            self.session, user_sid, skip, limit
        )

        chat_infos = [
            await self._map_chat_to_short_info(chat, user_sid) for chat in chats
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
            await self.chats_repo.remove_all_users_from_chat(self.session, chat_sid)
            await self.chats_repo.delete(self.session, chat)
            await self.session.commit()

    async def leave_or_clear_chat(self, chat_sid: UUID, current_user_sid: UUID) -> None:
        await self.chats_repo.remove_user_from_chat(
            self.session, chat_sid, current_user_sid
        )

        participants_count = await self.chats_repo.count_chat_participants(
            self.session, chat_sid
        )

        if participants_count == 0:
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
        user_chat = await self.chats_repo.get_user_chat(
            self.session, chat_sid, current_user_sid
        )

        if not user_chat:
            raise BackendException(
                status_code=403,
                result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
            )

        update_data = {}

        if chat_name is not None:
            if user_chat.role != "admin":
                raise BackendException(
                    status_code=403,
                    result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED),
                )
            chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
            if chat:
                update_data["chat_name"] = chat_name

        if avatar is not None:
            chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
            if chat and user_chat.role == "admin":
                update_data["avatar"] = avatar

        if is_pinned is not None:
            update_data["is_pinned"] = is_pinned
        if is_muted is not None:
            update_data["is_muted"] = is_muted

        if update_data:
            if "chat_name" in update_data or "avatar" in update_data:
                chat = await self.chats_repo.get_by_sid(self.session, chat_sid)
                if chat:
                    chat_update = {
                        k: v
                        for k, v in update_data.items()
                        if k in ["chat_name", "avatar"]
                    }
                    if chat_update:
                        await self.chats_repo.update(self.session, chat, chat_update)

            user_update = {
                k: v for k, v in update_data.items() if k in ["is_pinned", "is_muted"]
            }
            if user_update:
                await self.chats_repo.update(self.session, user_chat, user_update)

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
