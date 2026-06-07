from random import choice
from typing import Annotated
from uuid import UUID

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import Pagination, ResultBase
from app.database import Users, get_session

from .schemas import GetUsersResponse, UserCreate, UserDTO, UserResponse
from .user_repo import UsersRepository, get_user_repo

avatars = [
    "https://static.wikia.nocookie.net/mems/images/b/b3/%D0%9E%D0%BA%D0%B0%D0%BA.webp/revision/latest/scale-to-width-down/1200?cb=20260102083423&path-prefix=ru",
    "https://spbcult.ru/upload/iblock/7b9/9n0tc4etzlpw3t1h1021gjzhwl226j5k.jpg",
    "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg",
    "https://i.pinimg.com/originals/6f/b7/26/6fb726d46f5894ed0c67399b8b42f4c0.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRAoIwxxUyWwjjPlHfFOG7_vXwn19Muf8B8QA&s",
    None,
]


class UserService:
    def __init__(self, user_repo: UsersRepository, session: AsyncSession):
        self.user_repo = user_repo
        self.session = session

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

        return UserDTO.model_validate(user)

    async def create_user(self, user: UserCreate) -> UserDTO:
        user.avatar = choice(avatars)
        print("aa")
        user_to_create = Users(**user.model_dump())
        await self.user_repo.create(obj=user_to_create, session=self.session)
        await self.session.commit()
        await self.session.refresh(user_to_create)

        return UserDTO.model_validate(user_to_create)

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
            items=[UserResponse.model_validate(user) for user in users],
            pagination=Pagination(
                limit=pagination_params.limit, offset=pagination_params.offset
            ),
            total=total,
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
            items=[UserResponse.model_validate(user) for user in users],
            pagination=Pagination(
                limit=pagination_params.limit, offset=pagination_params.offset
            ),
            total=total,
        )


async def get_user_service(
    user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserService:
    return UserService(user_repo=user_repo, session=session)
