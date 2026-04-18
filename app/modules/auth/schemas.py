from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(UserLogin):
    name: str
    surname: str
    username: str
    avatar: str
    password: str

class UserTokens(BaseModel):
    user_sid: UUID
    access_token: str
    refresh_token: str


class UserRefreshToken(BaseModel):
    refresh_token: str