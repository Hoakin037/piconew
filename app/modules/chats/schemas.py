from uuid import UUID

from pydantic import BaseModel, ConfigDict
from typing import Literal

from modules.messages.schemas import MessageResponse
from modules.users.schemas import ChatParticipant


class ChatsBase(BaseModel):
    chat_name: str
    chat_type: Literal['persona', 'group', 'chat']
    avatar: str

class ChatsInDB(ChatsBase):
    pass

class ChatsCreate(ChatsBase):
    user_sid: UUID


class ChatsResponse(ChatsBase):
    sid: UUID
    is_pinned: bool = False
    is_muted: bool = False
    created_at: str

    lastMessage: list[MessageResponse] = []
    participants: list[ChatParticipant] = []
