from uuid import UUID

from app.common.schemas import CoreSchema
from app.modules.users.schemas import UserLastMessage, UserResponse


class MessageBase(CoreSchema):
    chat_sid: UUID
    content: str
    attachments: list = []
    reply_to: None
    user: UserResponse


class MessageResponse(CoreSchema):
    chat_sid: UUID
    content: str
    attachments: list = []
    reply_to: None
    user: UserLastMessage
    sid: UUID
    created_at: str
    updated_at: str
    is_deleted: bool = False
