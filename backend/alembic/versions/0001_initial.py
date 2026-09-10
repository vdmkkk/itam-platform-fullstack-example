"""Initial schema: streams, users, cards, votes, comments, board settings.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "streams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_streams")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("platform_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("telegram", sa.String(length=40), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["stream_id"], ["streams.id"], name=op.f("fk_users_stream_id_streams"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("stream_id", "id", name=op.f("uq_users_stream_id_id")),
        sa.UniqueConstraint(
            "stream_id", "platform_user_id", name=op.f("uq_users_stream_id_platform_user_id")
        ),
    )
    op.create_index(op.f("ix_users_stream_id"), "users", ["stream_id"])

    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["stream_id", "author_id"],
            ["users.stream_id", "users.id"],
            name=op.f("fk_cards_stream_id_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cards")),
        sa.UniqueConstraint("stream_id", "id", name=op.f("uq_cards_stream_id_id")),
    )
    op.create_index(op.f("ix_cards_author_id"), "cards", ["author_id"])
    op.create_index("ix_cards_stream_id_created_at", "cards", ["stream_id", "created_at"])

    op.create_table(
        "votes",
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("value IN (-1, 1)", name=op.f("ck_votes_value")),
        sa.ForeignKeyConstraint(
            ["stream_id", "card_id"],
            ["cards.stream_id", "cards.id"],
            name=op.f("fk_votes_stream_id_card_id_cards"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stream_id", "user_id"],
            ["users.stream_id", "users.id"],
            name=op.f("fk_votes_stream_id_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("card_id", "user_id", name=op.f("pk_votes")),
    )
    op.create_index("ix_votes_stream_id_card_id", "votes", ["stream_id", "card_id"])
    op.create_index("ix_votes_stream_id_user_id", "votes", ["stream_id", "user_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["stream_id", "card_id"],
            ["cards.stream_id", "cards.id"],
            name=op.f("fk_comments_stream_id_card_id_cards"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stream_id", "author_id"],
            ["users.stream_id", "users.id"],
            name=op.f("fk_comments_stream_id_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(op.f("ix_comments_author_id"), "comments", ["author_id"])
    op.create_index("ix_comments_card_id_created_at", "comments", ["card_id", "created_at"])
    op.create_index("ix_comments_stream_id_card_id", "comments", ["stream_id", "card_id"])

    op.create_table(
        "board_settings",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("accept_threshold", sa.Integer(), nullable=False),
        sa.Column("reject_threshold", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_board_settings_singleton")),
        sa.CheckConstraint(
            "accept_threshold >= 1 AND reject_threshold >= 1",
            name=op.f("ck_board_settings_thresholds_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_board_settings")),
    )


def downgrade() -> None:
    op.drop_table("board_settings")
    op.drop_table("comments")
    op.drop_table("votes")
    op.drop_table("cards")
    op.drop_table("users")
    op.drop_table("streams")
