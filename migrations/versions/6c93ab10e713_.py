"""empty message

Revision ID: 6c93ab10e713
Revises: f932ca9eb679
Create Date: 2026-04-12 15:23:05.507692

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c93ab10e713"
down_revision: Union[str, Sequence[str], None] = "f932ca9eb679"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("messages_reply_message_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_sender_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_chat_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("userschats_user_id_fkey", "userschats", type_="foreignkey")
    op.drop_constraint("userschats_chat_id_fkey", "userschats", type_="foreignkey")

    op.drop_column("messages", "chat_id")
    op.drop_column("messages", "id")
    op.drop_column("messages", "sender_id")
    op.drop_column("messages", "reply_message_id")
    op.drop_column("userschats", "user_id")
    op.drop_column("userschats", "chat_id")
    op.drop_column("users", "id")
    op.drop_column("chats", "id")

    op.add_column("users", sa.Column("sid", sa.UUID(), nullable=False))
    op.add_column("users", sa.Column("status", sa.String(length=72), nullable=False))
    op.add_column("users", sa.Column("avatar", sa.String(length=100), nullable=True))
    op.add_column("chats", sa.Column("sid", sa.UUID(), nullable=False))
    op.add_column("chats", sa.Column("avatar", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("sid", sa.UUID(), nullable=False))
    op.add_column("messages", sa.Column("sender_sid", sa.UUID(), nullable=False))
    op.add_column("messages", sa.Column("chat_id", sa.UUID(), nullable=False))
    op.add_column("messages", sa.Column("reply_message_sid", sa.UUID(), nullable=True))
    op.add_column("userschats", sa.Column("user_sid", sa.UUID(), nullable=False))
    op.add_column("userschats", sa.Column("chat_sid", sa.UUID(), nullable=False))
    op.add_column(
        "userschats",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "userschats",
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_primary_key("users_pkey", "users", ["sid"])
    op.create_primary_key("chats_pkey", "chats", ["sid"])
    op.create_primary_key("messages_pkey", "messages", ["sid"])
    op.create_primary_key("userschats_pkey", "userschats", ["user_sid", "chat_sid"])

    op.create_foreign_key(
        "fk_messages_sender_sid", "messages", "users", ["sender_sid"], ["sid"]
    )
    op.create_foreign_key(
        "fk_messages_reply_sid", "messages", "messages", ["reply_message_sid"], ["sid"]
    )
    op.create_foreign_key(
        "fk_messages_chat_id", "messages", "chats", ["chat_id"], ["sid"]
    )
    op.create_foreign_key(
        "fk_userschats_user_sid", "userschats", "users", ["user_sid"], ["sid"]
    )
    op.create_foreign_key(
        "fk_userschats_chat_sid", "userschats", "chats", ["chat_sid"], ["sid"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_sender_sid", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_reply_sid", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_chat_id", "messages", type_="foreignkey")
    op.drop_constraint("fk_userschats_user_sid", "userschats", type_="foreignkey")
    op.drop_constraint("fk_userschats_chat_sid", "userschats", type_="foreignkey")

    op.drop_constraint("users_pkey", "users", type_="primary")
    op.drop_constraint("chats_pkey", "chats", type_="primary")
    op.drop_constraint("messages_pkey", "messages", type_="primary")
    op.drop_constraint("userschats_pkey", "userschats", type_="primary")

    op.drop_column("userschats", "is_muted")
    op.drop_column("userschats", "is_pinned")
    op.drop_column("userschats", "chat_sid")
    op.drop_column("userschats", "user_sid")
    op.drop_column("messages", "reply_message_sid")
    op.drop_column("messages", "chat_id")
    op.drop_column("messages", "sender_sid")
    op.drop_column("messages", "sid")
    op.drop_column("users", "avatar")
    op.drop_column("users", "status")
    op.drop_column("users", "sid")
    op.drop_column("chats", "avatar")
    op.drop_column("chats", "sid")

    op.add_column(
        "users", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False)
    )
    op.add_column(
        "chats", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False)
    )
    op.add_column(
        "messages", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False)
    )
    op.add_column("messages", sa.Column("sender_id", sa.Integer(), nullable=False))
    op.add_column("messages", sa.Column("chat_id", sa.Integer(), nullable=False))
    op.add_column(
        "messages", sa.Column("reply_message_id", sa.Integer(), nullable=True)
    )
    op.add_column("userschats", sa.Column("user_id", sa.Integer(), nullable=False))
    op.add_column("userschats", sa.Column("chat_id", sa.Integer(), nullable=False))

    op.create_primary_key("users_pkey", "users", ["id"])
    op.create_primary_key("chats_pkey", "chats", ["id"])
    op.create_primary_key("messages_pkey", "messages", ["id"])
    op.create_primary_key("userschats_pkey", "userschats", ["user_id", "chat_id"])

    op.create_foreign_key(
        "messages_sender_id_fkey", "messages", "users", ["sender_id"], ["id"]
    )
    op.create_foreign_key(
        "messages_chat_id_fkey", "messages", "chats", ["chat_id"], ["id"]
    )
    op.create_foreign_key(
        "messages_reply_message_id_fkey",
        "messages",
        "messages",
        ["reply_message_id"],
        ["id"],
    )
    op.create_foreign_key(
        "userschats_user_id_fkey", "userschats", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "userschats_chat_id_fkey", "userschats", "chats", ["chat_id"], ["id"]
    )
