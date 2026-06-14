from datetime import datetime
from uuid import UUID

from pydantic import EmailStr

from app.common.schemas import CoreSchema, ResultResponse
from app.modules.files.schemas import FileInfo


class UserLogin(CoreSchema):
    email: EmailStr
    password: str


class UserTokens(CoreSchema):
    access_token: str
    refresh_token: str


class UserRegister(UserLogin):
    name: str
    surname: str
    username: str
    password: str
    birthday: datetime | None


class UserLoginResponse(UserTokens, ResultResponse):
    sid: UUID
    name: str
    surname: str
    username: str
    email: str
    avatar: FileInfo | None
    birthday: datetime | None


class UserRefreshToken(CoreSchema):
    refresh_token: str


class UserRefreshTokenResponse(UserTokens, ResultResponse):
    pass
