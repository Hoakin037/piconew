from typing import Literal
from uuid import UUID

from  app.common.schemas import CoreSchema, ResultResponse


class UserBase(CoreSchema):
    name: str
    surname: str
    username: str
    email: str
    avatar: str | None = None



class UserCreate(UserBase):
    status: str = ""
    is_active: bool = False
    password: str

class UserDTO(UserBase):
    sid: UUID
    status: str
    is_active: bool

class ChatParticipant(UserBase):
    role: Literal['admin', 'member'] = 'member'
    joined_at: str
    left_at: str

class UserResponse(UserBase, ResultResponse):
    pass

