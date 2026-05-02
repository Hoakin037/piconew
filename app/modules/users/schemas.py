from typing import Literal
from uuid import UUID

from app.common.schemas import CoreSchema, ResultResponse


class UserBase(CoreSchema):
    name: str
    surname: str
    username: str
    email: str
    avatar: str | None = (
        "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg"
    )


class UserCreate(UserBase):
    status: str = ""
    is_active: bool = False
    password: str


class UserDTO(UserBase):
    sid: UUID
    status: str
    is_active: bool


class ChatParticipant(UserBase):
    role: Literal["admin", "member"] = "member"
    joined_at: str
    left_at: str


class UserResponse(UserBase, ResultResponse):
    pass


class UserLastMessage(CoreSchema):
    sid: UUID
    name: str
    surname: str
    username: str
