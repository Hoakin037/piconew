from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.common.core.jwt import get_current_user

from .schemas import (
    UserLogin,
    UserRegister,
    UserRefreshToken
)
from .auth_service import AuthService,    get_auth_service

from app.modules.users import UserDTO, UserService, get_user_service

auth = APIRouter(prefix="/auth", tags=["Auth"])


@auth.post(path="/signup", response_model=UserDTO, status_code=201)
async def register_new_user(
    user: UserRegister,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    new_user = await auth_service.register_user(user)
    new_user = await user_service.create_user(new_user)

    return new_user


@auth.post(path="/login", status_code=200)
async def login_user(
    user: UserLogin, auth_service: AuthService = Depends(get_auth_service)
):
    user_tokens = await auth_service.login_user(user)

    user_login_response = {
        "user_id": user_tokens.user_sid,
        "access_token": user_tokens.access_token,
        "refresh_token": user_tokens.refresh_token,
    }
    # response.set_cookie(
    #     key="refresh_token",
    #     value=user_tokens.refresh_token,
    #     httponly=False,
    #     secure=False,
    #     samesite="lax",
    #     max_age=3600,
    # )

    return user_login_response


@auth.post(path="/logout", status_code=204)
async def logout_user(
    refresh_token: UserRefreshToken,
    auth_service: AuthService = Depends(get_auth_service)
):

    await auth_service.logout_user(
       refresh_token.refresh_token
    )
    return



@auth.post(path="/refresh_tokens", status_code=200)
async def refresh_tokens(
    refresh_token: UserRefreshToken,
    auth_service: AuthService = Depends(get_auth_service),
):

    user_new_tokens = await auth_service.refresh_tokens(
        refresh_token.refresh_token
    )
    user_refresh_tokens_response = {
        "access_token": user_new_tokens.access_token,
        "refresh_token": user_new_tokens.refresh_token
    }
    # response.set_cookie(
    #     key="refresh_token",
    #     value=user_new_tokens.refresh_token,
    #     max_age=3600,
    #     secure=False,
    #     samesite="lax",
    #     httponly=False,
    # )
    return user_refresh_tokens_response

    raise HTTPException(status_code=401, detail="refresh токен не передан.")


@auth.get(path="/chats", status_code=200)
async def check_jwt(current_user: UUID = Depends(get_current_user)):
    if current_user:
        return {"user_id": current_user}
    raise HTTPException(status_code=404, detail="Пользователь не найден")
