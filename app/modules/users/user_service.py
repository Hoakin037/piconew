from typing import Annotated
from uuid import UUID

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.database import Users, get_session

from .schemas import UserCreate, UserDTO
from .user_repo import UsersRepository, get_user_repo


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
            user = await self.user_repo.get_by_sid(
                self.session, user_sid
            )  # Исправлено: session сначала
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
        user_to_create = Users(**user.model_dump())
        await self.user_repo.create(obj=user_to_create, session=self.session)
        await self.session.commit()
        await self.session.refresh(user_to_create)

        return UserDTO.model_validate(user_to_create)


async def get_user_service(
    user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserService:
    return UserService(user_repo=user_repo, session=session)
