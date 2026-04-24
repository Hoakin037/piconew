from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, func, UUID

import uuid
from datetime import datetime
from typing import Optional


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(36), nullable=False)
    surname: Mapped[str] = mapped_column(String(36), nullable=False)
    username: Mapped[str] = mapped_column(String(72), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(72), nullable=False)
    avatar: Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(144), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False)

    users_chats: Mapped[list["UsersChats"]] = relationship(
        "UsersChats", back_populates="users"
    )
    users_messages: Mapped[list["Messages"]] = relationship(
        "Messages", back_populates="users"
    )


class Chats(Base):
    __tablename__ = "chats"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_name: Mapped[str] = mapped_column(String(72), nullable=False)
    avatar: Mapped[str] = mapped_column(String(100), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False)

    users_chats: Mapped[list["UsersChats"]] = relationship(
        "UsersChats", back_populates="chats"
    )
    chat_messages: Mapped[list["Messages"]] = relationship(
        "Messages", back_populates="chats"
    )


#
class UsersChats(Base):
    __tablename__ = "userschats"

    user_sid: Mapped[UUID] = mapped_column(ForeignKey("users.sid"), primary_key=True)
    chat_sid: Mapped[UUID] = mapped_column(ForeignKey("chats.sid"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    is_muted: Mapped[bool] = mapped_column(default=False)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    chats: Mapped["Chats"] = relationship("Chats", back_populates="users_chats")
    users: Mapped["Users"] = relationship("Users", back_populates="users_chats")


class Messages(Base):
    __tablename__ = "messages"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_sid: Mapped[UUID] = mapped_column(ForeignKey("users.sid"), nullable=False)
    chat_sid: Mapped[UUID] = mapped_column(ForeignKey("chats.sid"))
    content: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )
    reply_message_sid: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("messages.sid"), nullable=True
    )

    chats: Mapped["Chats"] = relationship("Chats", back_populates="chat_messages")
    users: Mapped["Users"] = relationship("Users", back_populates="users_messages")

    # Само-связь (ответы)
    replied_to: Mapped[Optional["Messages"]] = relationship(
        "Messages",
        remote_side=[sid],
        back_populates="replies",
    )
    replies: Mapped[list["Messages"]] = relationship(
        "Messages",
        back_populates="replied_to",
    )
