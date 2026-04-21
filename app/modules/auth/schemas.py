from uuid import UUID

from pydantic import BaseModel, EmailStr
from app.common.schemas import ResultResponse, CoreSchema

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
    avatar: str
    password: str

class UserLoginResponse(UserTokens, ResultResponse):
    sid: UUID
    name: str
    surname: str
    username: str
    email: str
    avatar: str



class UserRefreshToken(CoreSchema):
    refresh_token: str

class UserRefreshTokenResponse(UserTokens, ResultResponse):
    pass