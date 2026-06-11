from typing import Literal
from uuid import UUID

from app.common.schemas import CoreSchema, ResultBase
from app.common.schemas.pagination import PaginationResult


class UserBase(CoreSchema):
    name: str
    surname: str
    username: str
    email: str


class UserCreate(UserBase):
    is_active: bool = False
    password: str


class UserDTO(UserBase):
    sid: UUID
    avatar: str | None
    status: str | None
    is_active: bool


class ChatParticipant(UserBase):
    role: Literal["admin", "member"] = "member"
    joined_at: str
    left_at: str


class UserResponse(UserBase):
    sid: UUID
    avatar: str | None
    status: str | None


class UserMessage(CoreSchema):
    sid: UUID
    name: str
    surname: str
    username: str
    avatar: str | None


class UserSearch(CoreSchema):
    search: str


class GetUsersResponse(CoreSchema):
    result: ResultBase
    items: list[UserResponse]
    pagination: PaginationResult
