from typing import Annotated
from uuid import UUID

from fastapi import HTTPException
from fastapi.params import Depends
from pwdlib import PasswordHash

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.core import JWTManager, RedisManager, get_jwt_manager, get_redis_manager
from app.database import Users, get_session
from .schemas import UserRegister, UserLogin, UserTokens
from app.modules.users import UsersRepository, UserDTO, get_user_repo
from app.modules.users.schemas import UserCreate


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UsersRepository,
        jwt_manager: JWTManager,
        redis_manager: RedisManager,
    ):
        self.user_repo = user_repo
        self._jwt_manager = jwt_manager
        self.session = session
        self._pwd_context = PasswordHash.recommended()
        self._redis_manager = redis_manager


    async def get_user_by_id(self, user_sid: UUID) -> UserDTO:
        user = await self.user_repo.get_user_by_sid(user_sid, self.session)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return UserDTO.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserDTO:
        user = await self.user_repo.get_user_by_username(username, self.session)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return UserDTO.model_validate(user)

    async def get_user_by_email(self, email: str) -> Users:
        user = await self.user_repo.get_user_by_email(email, self.session)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    async def create_tokens(self, user_sid: UUID) -> UserTokens:
        payload = {"sub": str(user_sid)}
        access_token = await self._jwt_manager.create_token(payload, "access")
        refresh_token = await self._jwt_manager.create_token(payload, "refresh")
        # ttl_seconds = self._jwt_manager.get_refresh_token_ttl_seconds
        # await self._redis_manager.create_session(str(current_user.id), refresh_token, ttl_seconds)

        # mock
        await self._redis_manager.create_session(str(user_sid), refresh_token, 3600)

        return UserTokens(
            user_sid=user_sid, access_token=access_token, refresh_token=refresh_token
        )

    async def register_user(self, user: UserRegister) -> UserCreate:
        username = await self.user_repo.get_user_by_username(user.username, self.session)
        email = await self.user_repo.get_user_by_email(user.email, self.session)

        if any([username, email]):
            raise HTTPException(status_code=400, detail="User already exists")

        user.password = self._pwd_context.hash(user.password)

        return UserCreate.model_validate(user)

    async def login_user(self, user: UserLogin) -> UserTokens:
        current_user = await self.get_user_by_email(user.email)
        if not self._pwd_context.verify(user.password, current_user.password):
            raise HTTPException(status_code=400, detail="Incorrect Password")

        user_tokens = await self.create_tokens(current_user.sid)
        await self._redis_manager.create_session(str(current_user.sid), user_tokens.refresh_token, 3600)
        return user_tokens

    async def logout_user(self, refresh_token: str) -> None:

        current_user_sid = await self._jwt_manager.decode_token(refresh_token)
        current_user = await self.user_repo.get_user_by_sid(user_sid=current_user_sid, session=self.session)

        if not current_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден.")

        session = await self._redis_manager.get_session(refresh_token)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Пользователь уже вышел из аккаунта на данном устройстве.",
            )

        await self._redis_manager.revoke_session(refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> UserTokens:
        user_id = await self._jwt_manager.decode_token(refresh_token)
        current_user = await self.user_repo.get_user_by_sid(user_sid=user_id, session=self.session)
        user_session = await self._redis_manager.get_session(refresh_token)

        if not current_user and user_session:
            raise HTTPException(
                status_code=401,
                detail="Не корректный токен или пользователь не сущетсвует.",
            )

        await self._redis_manager.revoke_session(refresh_token)
        return await self.create_tokens(user_id)

async def get_auth_service(
        session: Annotated[ AsyncSession, Depends(get_session)],
        user_repo: Annotated[ UsersRepository, Depends(get_user_repo)],
        jwt_manager: Annotated[ JWTManager, Depends(get_jwt_manager)],
        redis_manager: Annotated[ RedisManager, Depends(get_redis_manager)],
) -> AuthService:
    return AuthService(session, user_repo, jwt_manager, redis_manager)