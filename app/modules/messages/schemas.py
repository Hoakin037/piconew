from uuid import UUID

from app.common.schemas import CoreSchema
from app.modules.users.schemas import UserMessage


class MessageBase(CoreSchema):
    chat_sid: UUID
    content: str
    attachments: list = []
    reply_to: None
    sender: UserMessage


class MessageResponse(CoreSchema):
    sid: UUID
    chat_sid: UUID

    content: str
    attachments: list = []
    reply_to: None

    user: UserMessage

    created_at: str
    updated_at: str
    is_deleted: bool = False


class MessageCreate(CoreSchema):
    chat_sid: UUID
    content: str
    attachments: list = []
    reply_to: None
    sender_sid: UUID
