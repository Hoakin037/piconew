from typing import Annotated
from uuid import UUID

from fastapi import UploadFile
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import Pagination, ResultBase
from app.common.schemas.pagination import PaginationResult
from app.database import Users, get_session
from app.modules.files.file_service import FilesService, get_file_service

from .schemas import GetUsersResponse, UpdateUserInfo, UserCreate, UserDTO, UserResponse
from .user_repo import UsersRepository, get_user_repo


class UserService:
    def __init__(
        self,
        user_repo: UsersRepository,
        session: AsyncSession,
        file_service: FilesService,
    ):
        self.user_repo = user_repo
        self.session = session
        self.file_service = file_service

    async def get_user(
        self,
        user_sid: UUID = None,
        username: str = None,
        email: str = None,
        as_model: bool = False,
    ) -> UserDTO | Users:
        user = None

        if user_sid is not None:
            user = await self.user_repo.get_by_sid(self.session, user_sid)
        elif username is not None:
            user = await self.user_repo.get_user_by_username(username, self.session)
        elif email is not None:
            user = await self.user_repo.get_user_by_email(email, self.session)

        if user is None:
            raise BackendException(
                status_code=401, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )
        if as_model:
            return user

        return await self._map_user(user)

    async def _map_user(self, user: Users, dto: bool = True) -> UserDTO | UserResponse:
        if dto:
            return UserDTO.model_validate(user)

        return UserResponse.model_validate(user)

    async def create_user(self, user: UserCreate) -> UserDTO:
        user_to_create = Users(**user.model_dump())
        await self.user_repo.create(obj=user_to_create, session=self.session)
        await self.session.commit()
        await self.session.refresh(user_to_create)

        return await self._map_user(user_to_create)

    async def search_global_users(
        self,
        user_sid: UUID,
        search_query: str | None,
        pagination_params: Pagination,
    ) -> GetUsersResponse:
        users, total = await self.user_repo.search_users(
            session=self.session,
            current_user_sid=user_sid,
            search_query=search_query,
            skip=pagination_params.offset,
            limit=pagination_params.limit,
        )

        return GetUsersResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            items=[await self._map_user(user, dto=False) for user in users],
            pagination=PaginationResult(
                limit=pagination_params.limit,
                offset=pagination_params.offset,
                total=total,
            ),
        )

    async def search_users_for_chat(
        self,
        user_sid: UUID,
        chat_sid: UUID,
        search_query: str | None,
        pagination_params: Pagination,
    ) -> GetUsersResponse:
        users, total = await self.user_repo.search_users_for_chat(
            session=self.session,
            current_user_sid=user_sid,
            chat_sid=chat_sid,
            search_query=search_query,
            skip=pagination_params.offset,
            limit=pagination_params.limit,
        )

        return GetUsersResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            items=[await self._map_user(user, dto=False) for user in users],
            pagination=PaginationResult(
                limit=pagination_params.limit,
                offset=pagination_params.offset,
                total=total,
            ),
        )

    async def upload_user_avatar(
        self, user_sid: UUID, file: UploadFile
    ) -> UserResponse:
        user = await self.get_user(user_sid, as_model=True)

        avatar = await self.file_service.create_img_file(
            file, temp=False, sid=user_sid, type="avatar"
        )

        user = await self.user_repo.update(
            obj=user,
            session=self.session,
            update_data={"avatar": avatar.model_dump(mode="json")},
        )
        await self.session.commit()
        await self.session.refresh(user)

        return await self._map_user(user, dto=False)

    async def change_user_info(
        self, new_info: UpdateUserInfo, user_sid: UUID
    ) -> UserResponse:
        user = await self.get_user(user_sid=user_sid, as_model=True)

        updated_user = await self.user_repo.update(
            obj=user,
            session=self.session,
            update_data=new_info.model_dump(exclude_unset=True, exclude_none=True),
        )

        return await self._map_user(updated_user, dto=False)


async def get_user_service(
    user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file_service: Annotated[FilesService, Depends(get_file_service)],
) -> UserService:
    return UserService(user_repo=user_repo, session=session, file_service=file_service)
