from typing import Literal
from uuid import uuid4, UUID

from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    name: str
    surname: str
    username: str
    email: str
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)


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



