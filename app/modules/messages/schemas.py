from uuid import UUID

from pydantic import BaseModel, ConfigDict

from modules.users.schemas import UserResponse


class MessageBase(BaseModel):
    chat_sid: UUID
    content: str
    attachments: list = []
    reply_to: None
    user: UserResponse


class MessageResponse(MessageBase):
    sid: UUID
    created_at: str
    updated_at: str
    is_deleted: bool = False
