from datetime import datetime
from random import choice
from typing import Any, Literal
from uuid import UUID

from pydantic import model_validator

from app.common.schemas import CoreSchema, Pagination, ResultBase
from app.modules.messages.schemas import MessageResponse
from app.modules.users.schemas import UserLastMessage

avatars = [
    "https://static.wikia.nocookie.net/mems/images/b/b3/%D0%9E%D0%BA%D0%B0%D0%BA.webp/revision/latest/scale-to-width-down/1200?cb=20260102083423&path-prefix=ru",
    "https://spbcult.ru/upload/iblock/7b9/9n0tc4etzlpw3t1h1021gjzhwl226j5k.jpg",
    "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg",
    "https://i.pinimg.com/originals/6f/b7/26/6fb726d46f5894ed0c67399b8b42f4c0.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRAoIwxxUyWwjjPlHfFOG7_vXwn19Muf8B8QA&s",
    None,
]


class BaseResponse(CoreSchema):
    result: ResultBase


class CreateChatRequest(CoreSchema):
    receiver_id: UUID


class CreateGroupRequest(CoreSchema):
    chat_name: str


class UpdateChatRequest(CoreSchema):
    chat_name: str = None
    avatar: str | None = choice(avatars)
    is_pinned: bool = False
    is_muted: bool = False


class ChatParticipantUser(CoreSchema):
    sid: UUID
    name: str
    surname: str
    email: str
    username: str = None
    avatar: str = choice(avatars)
    status: str | None = None
    is_active: bool
    created_at: datetime
    role: Literal["admin", "member"]
    joined_at: str
    left_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_user_fields(cls, data: Any):
        if hasattr(data, "users") and data.users:
            user = data.users
            result = {
                **user.__dict__,
                "role": data.role,
                "joined_at": data.joined_at.isoformat() if data.joined_at else "",
                "left_at": data.left_at.isoformat() if data.left_at else None,
            }
            return result
        return data


class ChatParticipant(CoreSchema):
    result: ResultBase
    user: ChatParticipantUser


class ShortChatInfo(CoreSchema):
    sid: UUID
    type: Literal["personal", "group"]
    chatName: str
    avatar: str | None = choice(avatars)
    last_message: MessageResponse = MessageResponse(
        chat_sid=UUID("b870ee88-cdc6-49ea-920a-996e16992d9d"),
        content="Breaking Bad",
        attachments=[],
        reply_to=None,
        user=UserLastMessage(
            sid=UUID("61d8f457-7c96-432c-9184-0d483b4c87bd"),
            name="Walter",
            surname="White",
            username="Хайзенберг",
        ),
        sid=UUID("61d8f457-7c96-432c-9184-0d483b4c87bd"),
        created_at="2026-05-01T12:00:00Z",
        updated_at="2026-05-01T12:00:00Z",
        is_deleted=False,
    )
    unread_count: int = 0
    is_pinned: bool
    is_muted: bool
    created_at: str


class FullChatInfo(ShortChatInfo):
    participants: list[ChatParticipantUser]
    attachments: list = []


class GetChatResponse(BaseResponse):
    chat: FullChatInfo


class GetChatsResponse(BaseResponse):
    chats: list[ShortChatInfo]
    pagination: Pagination
