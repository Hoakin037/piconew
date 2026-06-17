from typing import Annotated
from uuid import UUID

from fastapi import UploadFile
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.common.schemas.pagination import PaginationResult
from app.database import Chats, get_session
from app.modules.files.file_service import FilesService, get_file_service
from app.modules.files.schemas import ImageInfo
from app.modules.messages.postgres_repo import MessagesRepository, get_msg_repo
from app.modules.messages.schemas import MessageResponse
from app.modules.users.user_service import UserService, get_user_service

from .chats_repo import ChatsRepository
from .consts.custom_options import ChatsCustomOptions
from .schemas import (
    ChatParticipantUser,
    CreateGroupRequest,
    FullChatInfo,
    GetChatResponse,
    GetChatsResponse,
    ShortChatInfo,
)


class ChatsService:
    def __init__(
        self,
        session: AsyncSession,
        chats_repo: ChatsRepository,
        message_repo: MessagesRepository,
        user_service: UserService,
        file_service: FilesService,
    ):
        self.session = session
        self.chats_repo = chats_repo
        self.user_service = user_service
        self.message_repo = message_repo
        self.file_service = file_service

    async def create_notes(self, current_user_sid: UUID) -> GetChatResponse:
        current_user = await self.user_service.get_user(
            user_sid=current_user_sid, as_model=True
        )
        if not current_user:
            raise BackendException(
                status_code=404,
                result=ResultBase(code=CommonCodesEnum.NOT_FOUND),
            )

        chat_name = "Избранное"

        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_type="personal",
            ),
        )
        await self.session.flush()

        await self.chats_repo.add_participant(
            user_sid=current_user_sid,
            session=self.session,
            chat_sid=new_chat.sid,
            avatar=ImageInfo(
                url="https://img.icons8.ru/?size=48&id=26089&format=png",
                type="avatar",
                extension="image/png",
            ),
            chat_name=chat_name,
            role="admin",
        )

        await self.session.commit()

        return await self.get_chat_by_id(current_user_sid, new_chat.sid)

    async def create_personal_chat(
        self, current_user_sid: UUID, receiver_sid: UUID
    ) -> tuple[GetChatResponse, GetChatResponse]:
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

        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_type="chat",
                avatar=None,
            ),
        )
        await self.session.flush()

        await self.chats_repo.add_participant(
            session=self.session,
            user_sid=current_user_sid,
            chat_name=receiver.name + " " + receiver.surname,
            avatar=receiver.avatar,
            chat_sid=new_chat.sid,
            role="admin",
        )
        await self.chats_repo.add_participant(
            session=self.session,
            user_sid=receiver_sid,
            chat_sid=new_chat.sid,
            chat_name=current_user.name + " " + current_user.surname,
            avatar=current_user.avatar,
            role="admin",
        )

        await self.session.commit()

        user_chat = await self.get_chat_by_id(current_user_sid, new_chat.sid)
        other_chat = await self.get_chat_by_id(receiver_sid, new_chat.sid)

        return (
            GetChatResponse(
                result=ResultBase(code=CommonCodesEnum.DEFAULT),
                chat=await self._map_chat_to_full_info(new_chat, current_user_sid),
            ),
            GetChatResponse(
                result=ResultBase(code=CommonCodesEnum.DEFAULT),
                chat=await self._map_chat_to_full_info(new_chat, receiver_sid),
            ),
        )

    async def create_group_chat(
        self,
        current_user_sid: UUID,
        group_info: CreateGroupRequest,
    ) -> GetChatResponse:
        new_chat = await self.chats_repo.create(
            session=self.session,
            obj=Chats(
                chat_name=group_info.chat_name,
                chat_type="group",
                avatar=None,
            ),
        )
        await self.session.flush()

        await self.chats_repo.add_participant(
            self.session,
            user_sid=current_user_sid,
            chat_sid=new_chat.sid,
            avatar=None,
            chat_name=new_chat.chat_name,
            role="admin",
        )
        for user in group_info.members:
            await self.chats_repo.add_participant(
                self.session,
                chat_sid=new_chat.sid,
                avatar=None,
                chat_name=new_chat.chat_name,
                role="member",
                user_sid=user,
            )

        await self.session.commit()

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

    async def add_group_members(
        self, group_sid: UUID, user_sid: UUID, members: list[UUID]
    ) -> GetChatResponse:
        chat = await self.get_chat_by_id(
            user_sid=user_sid, chat_sid=group_sid, as_model=True
        )

        if not await self.chats_repo.check_if_user_admin(
            chat_sid=group_sid, user_sid=user_sid, session=self.session
        ):
            raise BackendException(
                status_code=403, result=ResultBase(code=CommonCodesEnum.ACCESS_DENIED)
            )

        for user in members:
            await self.chats_repo.add_participant(
                self.session, user, group_sid, "member", chat_name=chat.chat_name
            )

        await self.session.commit()
        self.session.expire_all()

        chat_with_details = await self.chats_repo.get_chat_with_options(
            self.session, group_sid, ChatsCustomOptions.with_all()
        )
        if not chat_with_details:
            raise BackendException(
                status_code=404, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_full_info(chat_with_details, user_sid),
        )

    async def _map_chat_to_short_info(
        self, chat: Chats, current_user_sid: UUID
    ) -> ShortChatInfo:
        user_chat = None
        other_chat = None
        chat_name = None

        for uc in chat.users_chats:
            if str(uc.user_sid) == str(current_user_sid):
                user_chat = uc
            else:
                other_chat = uc

        last_message = await self.message_repo.get_last_message_in_chat(
            session=self.session, chat_sid=chat.sid
        )
        wallpaper = None
        if chat.chat_type == "personal":
            avatar, wallpaper, chat_name = (
                user_chat.avatar if user_chat else None,
                user_chat.wallpaper if user_chat else None,
                user_chat.chat_name if user_chat else None,
            )
        elif chat.chat_type == "chat":
            avatar = (
                other_chat.user.avatar
                if other_chat and other_chat.user
                else (user_chat.avatar if user_chat else None)
            )

            wallpaper = user_chat.wallpaper if user_chat else None
            chat_name = (
                other_chat.user.name + " " + other_chat.user.surname
                if other_chat
                else (user_chat.chat_name if user_chat else None)
            )
        else:
            avatar = chat.avatar
            chat_name = chat.chat_name
            wallpaper = user_chat.wallpaper if user_chat else None

        return ShortChatInfo(
            sid=chat.sid,
            type=chat.chat_type,
            chat_name=chat_name,
            avatar=ImageInfo.model_validate(avatar) if avatar else None,
            unread_count=0,
            is_pinned=user_chat.is_pinned if user_chat else False,
            is_muted=user_chat.is_muted if user_chat else False,
            created_at=chat.created_at.isoformat() if chat.created_at else "",
            wallpaper=ImageInfo.model_validate(wallpaper) if wallpaper else None,
            last_message=MessageResponse(**last_message.__dict__, attachments=[])
            if last_message
            else None,
        )

    async def _map_chat_to_full_info(
        self, chat: Chats, current_user_sid: UUID
    ) -> FullChatInfo:
        participants = []
        user_chat = None
        other_chat = None
        chat_name = None

        for uc in chat.users_chats:
            if str(uc.user_sid) == str(current_user_sid):
                user_chat = uc
            else:
                other_chat = uc
            participants.append(ChatParticipantUser.model_validate(uc))

        last_message = await self.message_repo.get_last_message_in_chat(
            session=self.session, chat_sid=chat.sid
        )

        for uc in chat.users_chats:
            if str(uc.user_sid) == str(current_user_sid):
                user_chat = uc
            else:
                other_chat = uc

        last_message = await self.message_repo.get_last_message_in_chat(
            session=self.session, chat_sid=chat.sid
        )
        wallpaper = None
        if chat.chat_type == "personal":
            avatar, wallpaper, chat_name = (
                user_chat.avatar if user_chat else None,
                user_chat.wallpaper if user_chat else None,
                user_chat.chat_name if user_chat else None,
            )
        elif chat.chat_type == "chat":
            avatar = (
                other_chat.user.avatar
                if other_chat and other_chat.user
                else (user_chat.avatar if user_chat else None)
            )

            wallpaper = user_chat.wallpaper if user_chat else None
            chat_name = (
                other_chat.user.name + " " + other_chat.user.surname
                if other_chat
                else (user_chat.chat_name if user_chat else None)
            )
        else:
            avatar = chat.avatar
            chat_name = chat.chat_name
            wallpaper = user_chat.wallpaper if user_chat else None

        return FullChatInfo(
            sid=chat.sid,
            type=chat.chat_type,
            chat_name=chat_name,
            avatar=ImageInfo.model_validate(avatar) if avatar else None,
            unread_count=0,
            participants=participants,
            is_pinned=user_chat.is_pinned if user_chat else False,
            is_muted=user_chat.is_muted if user_chat else False,
            created_at=chat.created_at.isoformat(),
            wallpaper=ImageInfo.model_validate(wallpaper) if wallpaper else None,
            attachments=[],
            last_message=MessageResponse(**last_message.__dict__, attachments=[])
            if last_message
            else None,
        )

    async def get_chat_by_id(
        self, user_sid: UUID, chat_sid: UUID, as_model: bool = False
    ) -> GetChatResponse | Chats:
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

        if as_model:
            return chat

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_full_info(chat, user_sid),
        )

    async def get_user_chats(
        self, user_sid: UUID, skip: int = 0, limit: int = 50
    ) -> GetChatsResponse:
        chats, total = await self.chats_repo.get_filtered_with_details(
            self.session, user_sid, skip, limit
        )

        chat_infos = [
            await self._map_chat_to_short_info(chat, user_sid) for chat in chats
        ]

        return GetChatsResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chats=chat_infos,
            pagination=PaginationResult(limit=limit, offset=skip, total=total),
        )

    async def delete_chat(self, chat_sid: UUID, current_user_sid: UUID) -> None:
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

    async def set_group_avatar(
        self, chat_sid: UUID, file: UploadFile, user_sid: UUID
    ) -> GetChatResponse:
        chat = await self.get_chat_by_id(user_sid, chat_sid, as_model=True)

        avatar = await self.file_service.create_img_file(
            file, temp=False, sid=chat_sid, type="avatar"
        )

        chat = await self.chats_repo.update(
            self.session,
            obj=chat,
            update_data={"avatar": avatar.model_dump(mode="json")},
        )
        await self.session.commit()
        await self.session.refresh(chat)

        chat_with_details = await self.chats_repo.get_chat_with_options(
            self.session, chat_sid, ChatsCustomOptions.with_all()
        )

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_full_info(chat_with_details, user_sid),
        )

    async def set_wallpaper(
        self, chat_sid: UUID, file: UploadFile, user_sid: UUID
    ) -> GetChatResponse:
        chat = await self.chats_repo.get_user_chat(
            session=self.session, user_sid=user_sid, chat_sid=chat_sid
        )
        if not chat:
            raise BackendException(
                status_code=404, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )

        wallpaper = await self.file_service.create_img_file(
            file, temp=False, sid=chat_sid, type="wallpaper"
        )

        chat = await self.chats_repo.update(
            self.session,
            obj=chat,
            update_data={"wallpaper": wallpaper.model_dump(mode="json")},
        )
        await self.session.commit()
        await self.session.refresh(chat)

        chat_with_details = await self.chats_repo.get_chat_with_options(
            self.session, chat_sid, ChatsCustomOptions.with_all()
        )

        return GetChatResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            chat=await self._map_chat_to_full_info(chat_with_details, user_sid),
        )

    async def change_chat_name(
        self, new_name: str, chat_sid: UUID, user_sid: UUID
    ) -> GetChatResponse:
        chat = await self.chats_repo.get_user_chat(
            session=self.session, user_sid=user_sid, chat_sid=chat_sid
        )

        if not chat:
            raise BackendException(
                status_code=404, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )

        await self.chats_repo.udate_user_chat(
            session=self.session, obj=chat, update_data={"chat_name": new_name}
        )
        await self.session.commit()

        return await self.get_chat_by_id(user_sid, chat_sid)


async def get_chats_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    message_repo: Annotated[MessagesRepository, Depends(get_msg_repo)],
    file_service: Annotated[FilesService, Depends(get_file_service)],
) -> ChatsService:
    chats_repo = ChatsRepository()
    return ChatsService(
        session=session,
        chats_repo=chats_repo,
        user_service=user_service,
        message_repo=message_repo,
        file_service=file_service,
    )
