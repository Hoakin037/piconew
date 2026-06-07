from typing import Annotated
from uuid import UUID

from fastapi.params import Depends
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.consts import CommonCodesEnum
from app.common.core import JWTManager, RedisManager, get_jwt_manager, get_redis_manager
from app.common.errors import BackendException
from app.common.schemas import ResultBase
from app.database import Users, get_session
from app.modules.users import UserDTO, UsersRepository, get_user_repo
from app.modules.users.schemas import UserCreate

from .schemas import (
    UserLogin,
    UserLoginResponse,
    UserRefreshTokenResponse,
    UserRegister,
    UserTokens,
)


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

    async def get_user(
        self,
        user_sid: UUID = None,
        username: str = None,
        email: str = None,
        as_model: bool = False,
    ) -> UserDTO | Users:
        user_get_strategy = {
            "user_sid": await self.user_repo.get_by_sid(
                sid=user_sid, session=self.session
            ),
            "username": await self.user_repo.get_user_by_username(
                username, self.session
            ),
            "email": await self.user_repo.get_user_by_email(email, self.session),
        }
        fields = [
            ("user_sid", user_sid),
            ("username", username),
            ("email", email),
        ]

        user = None
        for key, value in fields:
            if value is not None:
                user = user_get_strategy.get(key, value)

        if user is None:
            raise BackendException(
                status_code=401, result=ResultBase(code=CommonCodesEnum.NOT_FOUND)
            )
        if as_model:
            return user

        return UserDTO.model_validate(user)

    async def create_tokens(self, user_sid: UUID) -> UserTokens:
        payload = {"sub": str(user_sid)}
        access_token = await self._jwt_manager.create_token(payload, "access")
        refresh_token = await self._jwt_manager.create_token(payload, "refresh")
        # ttl_seconds = self._jwt_manager.get_refresh_token_ttl_seconds
        # await self._redis_manager.create_session(str(current_user.id), refresh_token, ttl_seconds)

        # mock
        await self._redis_manager.create_session(str(user_sid), refresh_token, 3600)

        return UserTokens(access_token=access_token, refresh_token=refresh_token)

    async def register_user(self, user: UserRegister) -> UserCreate:
        username = await self.user_repo.get_user_by_username(
            username=user.username, session=self.session
        )
        email = await self.user_repo.get_user_by_email(
            email=user.email, session=self.session
        )

        if any([username, email]):
            raise BackendException(
                status_code=422,
                result=ResultBase(code=CommonCodesEnum.USER_ALREADY_EXISTS),
            )

        user.password = self._pwd_context.hash(user.password)

        return UserCreate.model_validate(user)

    async def login_user(self, user: UserLogin) -> UserLoginResponse:
        current_user = await self.get_user(email=user.email, as_model=True)
        if not self._pwd_context.verify(user.password, current_user.password):
            raise BackendException(
                status_code=400,
                result=ResultBase(code=CommonCodesEnum.INCORRECT_PASSWORD),
            )

        user_tokens = await self.create_tokens(current_user.sid)
        await self._redis_manager.create_session(
            str(current_user.sid), user_tokens.refresh_token, 3600
        )

        user_info = UserLoginResponse.model_validate(
            {
                **current_user.__dict__,
                "access_token": user_tokens.access_token,
                "refresh_token": user_tokens.refresh_token,
                "result": ResultBase(code=CommonCodesEnum.DEFAULT),
            }
        )
        return user_info

    async def logout_user(self, refresh_token: str) -> None:
        current_user_sid = await self._jwt_manager.decode_token(refresh_token)
        await self.get_user(user_sid=current_user_sid)

        session = await self._redis_manager.get_session(refresh_token)
        if not session:
            raise BackendException(
                status_code=404,
                result=ResultBase(code=CommonCodesEnum.USER_ALREADY_LOGOUT),
            )

        await self._redis_manager.revoke_session(refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> UserRefreshTokenResponse:
        user_id = await self._jwt_manager.decode_token(refresh_token)
        await self.get_user(user_sid=user_id)

        user_session = await self._redis_manager.get_session(refresh_token)

        if not user_session:
            raise BackendException(
                status_code=401,
                result=ResultBase(code=CommonCodesEnum.TOKEN_VALIDATION_ERROR),
            )

        await self._redis_manager.revoke_session(refresh_token)
        tokens = await self.create_tokens(user_id)

        return UserRefreshTokenResponse(
            result=ResultBase(code=CommonCodesEnum.DEFAULT),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_repo: Annotated[UsersRepository, Depends(get_user_repo)],
    jwt_manager: Annotated[JWTManager, Depends(get_jwt_manager)],
    redis_manager: Annotated[RedisManager, Depends(get_redis_manager)],
) -> AuthService:
    return AuthService(session, user_repo, jwt_manager, redis_manager)
