from fastapi import APIRouter, Depends, HTTPException

from app.common.consts import CommonCodesEnum
from app.common.schemas import ResultBase, ResultResponse
from app.modules.chats.chats_service import ChatsService, get_chats_service
from app.modules.users import UserService, get_user_service

from .auth_service import AuthService, get_auth_service
from .schemas import (
    UserLogin,
    UserLoginResponse,
    UserRefreshToken,
    UserRefreshTokenResponse,
    UserRegister,
)

auth = APIRouter(prefix="/auth", tags=["Auth"])


@auth.post(path="/signup", response_model=ResultResponse, status_code=201)
async def register_new_user(
    user: UserRegister,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    chats_service: ChatsService = Depends(get_chats_service),
):
    new_user = await auth_service.register_user(user)
    new_user = await user_service.create_user(new_user)

    # Создаем персональный чат с избранными (заметки)
    await chats_service.create_notes(current_user_sid=new_user.sid)

    return ResultResponse(
        result=ResultBase(
            code=CommonCodesEnum.DEFAULT,
        )
    )


@auth.post(path="/login", status_code=200, response_model=UserLoginResponse)
async def login_user(
    user: UserLogin, auth_service: AuthService = Depends(get_auth_service)
):
    user_tokens = await auth_service.login_user(user)

    # response.set_cookie(
    #     key="refresh_token",
    #     value=user_tokens.refresh_token,
    #     httponly=False,
    #     secure=False,
    #     samesite="lax",
    #     max_age=3600,
    # )

    return user_tokens


@auth.post(path="/logout", status_code=200, response_model=ResultResponse)
async def logout_user(
    refresh_token: UserRefreshToken,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.logout_user(refresh_token.refresh_token)
    return ResultResponse(result=ResultBase(code=CommonCodesEnum.DEFAULT))


@auth.post(
    path="/refresh_tokens", status_code=200, response_model=UserRefreshTokenResponse
)
async def refresh_tokens(
    refresh_token: UserRefreshToken,
    auth_service: AuthService = Depends(get_auth_service),
):
    user_new_tokens = await auth_service.refresh_tokens(refresh_token.refresh_token)
    # response.set_cookie(
    #     key="refresh_token",
    #     value=user_new_tokens.refresh_token,
    #     max_age=3600,
    #     secure=False,
    #     samesite="lax",
    #     httponly=False,
    # )
    return user_new_tokens

    raise HTTPException(status_code=401, detail="refresh токен не передан.")
