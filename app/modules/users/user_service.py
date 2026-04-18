from typing import Annotated
from uuid import UUID

from fastapi import HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Users, get_session
from .user_repo import UsersRepository, get_user_repo
from .schemas import UserDTO, UserCreate


class UserService:
    def __init__(
        self,
        user_repo: UsersRepository,
        session: AsyncSession
    ):
        self.user_repo = user_repo
        self.session = session

    async def get_user(
            self, user_sid: UUID = None,
            username: str = None,
            email: str=None) -> UserDTO:
        user_get_strategy = {
            "user_sid": self.user_repo.get_user_by_sid(user_sid, self.session),
            "username": self.user_repo.get_user_by_username(username, self.session),
            "email": self.user_repo.get_user_by_email(email, self.session),
        }
        fields = [
            ("user_sid", user_sid),
            ("username", username),
            ("email", email),
        ]

        user = None
        for key, value in fields:
            if value is not None:
                user = await user_get_strategy.get(key, value)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return UserDTO(user)


    async def create_user(
            self,
            user: UserCreate
    ) -> UserDTO:

        user_to_create = Users(**user.model_dump())
        await self.user_repo.create_user(user_to_create, self.session)
        await self.session.commit()
        await self.session.refresh(user_to_create)

        return UserDTO.model_validate(user_to_create)



async def get_user_service(
        user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
        session: Annotated[AsyncSession, Depends(get_session)]
) -> UserService:
    return UserService(user_repo=user_repo, session=session)