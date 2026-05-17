from datetime import datetime
from uuid import UUID

from app.common.schemas import CoreSchema, ResultBase
from app.common.schemas.pagination import CursorPagination
from app.modules.users.schemas import UserMessage


class MessageSession(CoreSchema):
    user_sid: str
    token: str
    connected_at: str


class MessageSend(CoreSchema):
    content: str
    attachments: list[str] = []
    reply_to: None


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
    attachments: list[str] = []
    reply_to: None | UUID = None

    user: UserMessage

    created_at: datetime
    updated_at: datetime | None = None
    is_deleted: bool = False


class MessageCreate(CoreSchema):
    sid: UUID | None = None
    chat_sid: UUID
    sender_sid: UUID
    attachments: list | None = []
    content: str
    reply_message_sid: None | UUID = None
    created_at: datetime | None = None


class GetMessagesResponse(CoreSchema):
    result: ResultBase
    items: list[MessageResponse]
    pagination: CursorPagination
