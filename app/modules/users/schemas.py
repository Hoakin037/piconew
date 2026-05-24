from random import choice
from typing import Literal
from uuid import UUID

from app.common.schemas import CoreSchema, Pagination, ResultBase

avatars = [
    "https://static.wikia.nocookie.net/mems/images/b/b3/%D0%9E%D0%BA%D0%B0%D0%BA.webp/revision/latest/scale-to-width-down/1200?cb=20260102083423&path-prefix=ru",
    "https://spbcult.ru/upload/iblock/7b9/9n0tc4etzlpw3t1h1021gjzhwl226j5k.jpg",
    "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg",
    "https://i.pinimg.com/originals/6f/b7/26/6fb726d46f5894ed0c67399b8b42f4c0.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRAoIwxxUyWwjjPlHfFOG7_vXwn19Muf8B8QA&s",
    None,
]


class UserBase(CoreSchema):
    name: str
    surname: str
    username: str
    email: str
    avatar: str | None = choice(avatars)
    status: str | None = "В полете мысли"


class UserCreate(UserBase):
    is_active: bool = False
    password: str


class UserDTO(UserBase):
    sid: UUID
    is_active: bool


class ChatParticipant(UserBase):
    role: Literal["admin", "member"] = "member"
    joined_at: str
    left_at: str


class UserResponse(UserBase):
    sid: UUID


class UserMessage(CoreSchema):
    sid: UUID
    name: str
    surname: str
    username: str
    avatar: str | None = choice(avatars)


class UserSearch(CoreSchema):
    search: str


class GetUsersResponse(CoreSchema):
    result: ResultBase
    items: list[UserResponse]
    pagination: Pagination
    total: int
