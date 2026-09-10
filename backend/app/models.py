"""Database models.

Streams are a hard partition. Every table carries `stream_id`, and every
foreign key includes it (`(stream_id, card_id) -> cards(stream_id, id)`), so
the database itself refuses a vote, a comment or a card whose parts come from
different streams.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import CardType

# The platform can report a student without a stream. Those students still get
# a world of their own: they all share this partition key, and nobody else does.
NO_STREAM_ID = uuid.UUID(int=0)


def created_at_column() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at_column() -> Mapped[dt.datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Stream(Base):
    """A work group (cohort) as reported by the course platform."""

    __tablename__ = "streams"
    __mapper_args__ = {"eager_defaults": True}

    # The platform's stream id, or NO_STREAM_ID.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()


class User(Base):
    """A member of one stream.

    Linked to the platform account through `platform_user_id`, never through
    the email. A student moved to another stream gets a fresh row there, so
    their old content stays in the old stream.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("stream_id", "id"),
        UniqueConstraint("stream_id", "platform_user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("streams.id", ondelete="CASCADE"), index=True
    )
    platform_user_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    # Copied from the platform on first sight, then owned by the student.
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(320))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    telegram: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stream_id", "author_id"], ["users.stream_id", "users.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("stream_id", "id"),
        Index("ix_cards_stream_id_created_at", "stream_id", "created_at"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    title: Mapped[str] = mapped_column(String(120))
    type: Mapped[CardType] = mapped_column(
        Enum(CardType, name="card_type", native_enum=False, length=20)
    )
    description: Mapped[str | None] = mapped_column(Text)
    preview: Mapped[str | None] = mapped_column(Text)
    # Unix time in seconds (UTC), exactly as the API sends and receives it.
    date: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    author: Mapped[User] = relationship(
        primaryjoin="and_(Card.stream_id == User.stream_id, Card.author_id == User.id)",
        foreign_keys="[Card.stream_id, Card.author_id]",
        viewonly=True,
        lazy="joined",
        innerjoin=True,
    )


class Vote(Base):
    """One user's vote on one card: +1 or -1."""

    __tablename__ = "votes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stream_id", "card_id"], ["cards.stream_id", "cards.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["stream_id", "user_id"], ["users.stream_id", "users.id"], ondelete="CASCADE"
        ),
        CheckConstraint("value IN (-1, 1)", name="value"),
        Index("ix_votes_stream_id_card_id", "stream_id", "card_id"),
        Index("ix_votes_stream_id_user_id", "stream_id", "user_id"),
    )
    __mapper_args__ = {"eager_defaults": True}

    card_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    stream_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    value: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["stream_id", "card_id"], ["cards.stream_id", "cards.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["stream_id", "author_id"], ["users.stream_id", "users.id"], ondelete="CASCADE"
        ),
        Index("ix_comments_card_id_created_at", "card_id", "created_at"),
        Index("ix_comments_stream_id_card_id", "stream_id", "card_id"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    card_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    author: Mapped[User] = relationship(
        primaryjoin="and_(Comment.stream_id == User.stream_id, Comment.author_id == User.id)",
        foreign_keys="[Comment.stream_id, Comment.author_id]",
        viewonly=True,
        lazy="joined",
        innerjoin=True,
    )


class BoardSettings(Base):
    """Vote thresholds: one row for the whole deployment, changed via the admin API."""

    __tablename__ = "board_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint(
            "accept_threshold >= 1 AND reject_threshold >= 1", name="thresholds_positive"
        ),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    accept_threshold: Mapped[int] = mapped_column(Integer)
    reject_threshold: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[dt.datetime] = updated_at_column()
