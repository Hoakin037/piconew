import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ARRAY, UUID, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(36), nullable=False)
    surname: Mapped[str] = mapped_column(String(36), nullable=False)
    birthday: Mapped[datetime] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(String(72), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(144), unique=True, nullable=False)

    status: Mapped[str] = mapped_column(String(72), nullable=True)
    avatar: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=True)

    password: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now() AT TIME ZONE 'UTC'")
    )

    users_chats: Mapped[list["UsersChats"]] = relationship(
        "UsersChats", back_populates="user"
    )
    users_messages: Mapped[list["Messages"]] = relationship(
        "Messages", back_populates="user"
    )


class Chats(Base):
    __tablename__ = "chats"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    avatar: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=True)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now() AT TIME ZONE 'UTC'")
    )
    chat_name: Mapped[str] = mapped_column(String(72), nullable=True)

    users_chats: Mapped[list["UsersChats"]] = relationship(
        "UsersChats", back_populates="chats"
    )
    chat_messages: Mapped[list["Messages"]] = relationship(
        "Messages", back_populates="chats"
    )


class UsersChats(Base):
    __tablename__ = "userschats"

    user_sid: Mapped[UUID] = mapped_column(ForeignKey("users.sid"), primary_key=True)
    chat_sid: Mapped[UUID] = mapped_column(ForeignKey("chats.sid"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    is_muted: Mapped[bool] = mapped_column(default=False)
    chat_name: Mapped[str] = mapped_column(String(72), nullable=False)
    avatar: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=True)

    wallpaper: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=True)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now() AT TIME ZONE 'UTC'"),
        nullable=False,
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    chats: Mapped["Chats"] = relationship("Chats", back_populates="users_chats")
    user: Mapped["Users"] = relationship("Users", back_populates="users_chats")


class Messages(Base):
    __tablename__ = "messages"

    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_sid: Mapped[UUID] = mapped_column(ForeignKey("users.sid"), nullable=False)
    chat_sid: Mapped[UUID] = mapped_column(ForeignKey("chats.sid"))
    content: Mapped[str] = mapped_column(String(4000))
    reply_message_sid: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.sid"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now() AT TIME ZONE 'UTC'")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=text("now() AT TIME ZONE 'UTC'"),
    )

    is_deleted: Mapped[bool] = mapped_column(default=False)
    files_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    chats: Mapped["Chats"] = relationship("Chats", back_populates="chat_messages")
    user: Mapped["Users"] = relationship("Users", back_populates="users_messages")

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


class Files(Base):
    __tablename__ = "files"
    sid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(String(200), nullable=True)
    extension: Mapped[str] = mapped_column(String(50), nullable=True)
