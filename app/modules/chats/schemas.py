from uuid import UUID

from pydantic import BaseModel, ConfigDict
from typing import Literal

from modules.messages.schemas import MessageResponse
from modules.users.schemas import ChatParticipant


class ChatsBase(BaseModel):
    chat_name: str
    chat_type: Literal["personal", "group", "chat"]
    avatar: str


class ChatsInDB(ChatsBase):
    chat_sid: UUID

class UsersChatsInDB(BaseModel):
    role: Literal["admin", "member"] = "member"
    is_pinned: bool = False
    is_muted: bool = False
    joined_at: str
    left_at: str

class ChatsCreate(ChatsBase):
    user_sid: UUID
    receiver_sid: UUID


class ChatsResponse(ChatsBase):
    sid: UUID

    created_at: str

    lastMessage: MessageResponse = None
    participants: list[ChatParticipant] = []
    attachments: list[dict] = []
