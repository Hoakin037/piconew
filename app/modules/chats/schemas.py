from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import model_validator

from app.common.schemas import CoreSchema, ResultBase
from app.common.schemas.pagination import PaginationResult
from app.modules.files.schemas import FileInfo
from app.modules.messages.schemas import MessageResponse


class BaseResponse(CoreSchema):
    result: ResultBase


class CreateChatRequest(CoreSchema):
    receiver_id: UUID


class CreateGroupRequest(CoreSchema):
    chat_name: str
    members: list[UUID]


class AddGroupMembers(CoreSchema):
    members: list[UUID]


class UpdateChatRequest(CoreSchema):
    chat_name: str = None
    avatar: str | None
    is_pinned: bool = False
    is_muted: bool = False


class ChatParticipantUser(CoreSchema):
    sid: UUID
    name: str
    surname: str
    email: str
    username: str
    avatar: FileInfo | None
    status: str | None
    is_active: bool
    created_at: datetime
    role: Literal["admin", "member"]
    joined_at: str
    left_at: str | None

    @model_validator(mode="before")
    @classmethod
    def map_user_fields(cls, data: Any):
        if hasattr(data, "user") and data.user:
            user = data.user
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
    type: Literal["personal", "group", "chat"]
    chat_name: str
    avatar: FileInfo | None
    last_message: MessageResponse | None
    unread_count: int = 0
    is_pinned: bool
    is_muted: bool
    wallpaper: FileInfo | None
    created_at: str


class FullChatInfo(ShortChatInfo):
    participants: list[ChatParticipantUser]
    attachments: list = []


class GetChatResponse(BaseResponse):
    chat: FullChatInfo


class GetChatsResponse(BaseResponse):
    chats: list[ShortChatInfo]
    pagination: PaginationResult
