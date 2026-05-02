from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.common.schemas import ResultBase
from app.modules.messages.schemas import MessageResponse
from app.modules.users.schemas import UserLastMessage


class BaseResponse(BaseModel):
    result: ResultBase


class CreateChatRequest(BaseModel):
    type: Literal["chat"]
    receiver_id: UUID


class CreateGroupRequest(BaseModel):
    type: Literal["group"]
    chat_name: str


class UpdateChatRequest(BaseModel):
    chat_name: str = None
    avatar: str = "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg"
    is_pinned: bool = False
    is_muted: bool = False


class ChatParticipantUser(BaseModel):
    sid: UUID
    name: str
    surname: str
    email: str
    username: str = None
    avatar: str = "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg"
    status: str = None
    is_active: bool
    created_at: str
    role: Literal["admin", "member"]
    joined_at: str
    left_at: str | None = None


class ChatParticipant(BaseModel):
    result: ResultBase
    user: ChatParticipantUser


class ChatInfo(BaseModel):
    sid: UUID
    type: Literal["personal", "group", "chat"]
    chatName: str
    avatar: str = "https://sobakovod.club/uploads/posts/2021-12/1640661699_6-sobakovod-club-p-sobaki-sobaka-mem-8.jpg"
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
    participants: list[ChatParticipantUser]
    is_pinned: bool
    is_muted: bool
    created_at: str
    attachments: list = []


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int


class GetChatResponse(BaseResponse):
    chat: ChatInfo


class GetChatsResponse(BaseResponse):
    chats: list[ChatInfo]
    pagination: Pagination
