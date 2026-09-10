"""Domain logic shared by the routers: provisioning, stream-scoped lookups and card views.

Every lookup here filters by the caller's stream. A row from another stream
answers exactly like a row that doesn't exist (404), so ids can't be used
to probe other streams.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import Settings
from app.enums import CardColumn, CardSort, CardType, VoteValue
from app.identity import PlatformClient, PlatformStream, PlatformUser, RosterThrottle

logger = logging.getLogger(__name__)

NAME_MAX_LENGTH = 80
EMAIL_MAX_LENGTH = 320

CARD_NOT_FOUND = "Карточка не найдена. Возможно, её удалили."
COMMENT_NOT_FOUND = "Комментарий не найден. Возможно, его удалили."
USER_NOT_FOUND = "Пользователь не найден."

COLUMNS: tuple[tuple[CardColumn, str, str], ...] = (
    (CardColumn.event, "События", "Встречи, дедлайны, хакатоны: то, что происходит в определённый день."),
    (CardColumn.idea, "Идеи", "Предложения, за которые голосуют участники."),
    (CardColumn.question, "Вопросы", "То, на что кто-то хочет получить ответ."),
    (CardColumn.accepted, "Принято", "Карточки, чей счёт дошёл до порога принятия."),
    (CardColumn.rejected, "Отклонено", "Карточки, чей счёт опустился до минус порога отклонения."),
)


@dataclass
class Actor:
    """The student making the request, resolved to their row in their own stream."""

    user: models.User
    stream: models.Stream

    @property
    def stream_id(self) -> uuid.UUID:
        return self.stream.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------


def ensure_stream(db: Session, platform_stream: PlatformStream) -> models.Stream:
    """Return the caller's stream, creating it on first contact. New boards start empty."""
    stream_id = platform_stream.id or models.NO_STREAM_ID
    stream = db.get(models.Stream, stream_id)
    if stream is None:
        db.execute(
            pg_insert(models.Stream)
            .values(id=stream_id, code=platform_stream.code, title=platform_stream.title)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        db.commit()
        stream = db.get(models.Stream, stream_id)
        if stream is None:  # pragma: no cover - the row was committed just above
            raise RuntimeError(f"Stream {stream_id} vanished right after creation")
    elif platform_stream.id is not None and (stream.code, stream.title) != (
        platform_stream.code,
        platform_stream.title,
    ):
        stream.code = platform_stream.code
        stream.title = platform_stream.title
        db.commit()
    return stream


def _new_user_values(stream_id: uuid.UUID, member: PlatformUser) -> dict[str, Any]:
    """Profile defaults copied from the platform the first time we see someone."""
    return {
        "id": uuid.uuid4(),
        "stream_id": stream_id,
        "platform_user_id": member.id,
        "name": member.full_name[:NAME_MAX_LENGTH],
        "email": member.email[:EMAIL_MAX_LENGTH] if member.email else None,
        "avatar_url": member.avatar_url or None,
    }


def ensure_user(db: Session, stream: models.Stream, member: PlatformUser) -> models.User:
    """Return the caller's profile in this stream, creating it with platform defaults.

    After creation the profile belongs to the student: later platform changes
    never overwrite it.
    """
    query = select(models.User).where(
        models.User.stream_id == stream.id, models.User.platform_user_id == member.id
    )
    user = db.scalar(query)
    if user is None:
        db.execute(
            pg_insert(models.User)
            .values(**_new_user_values(stream.id, member))
            .on_conflict_do_nothing(index_elements=["stream_id", "platform_user_id"])
        )
        db.commit()
        user = db.scalar(query)
        if user is None:  # pragma: no cover
            raise RuntimeError("User vanished right after creation")
    return user


def sync_roster(db: Session, actor: Actor, platform: PlatformClient, throttle: RosterThrottle) -> None:
    """Add stream members who haven't used the API yet, so the people list is complete.

    Best effort: if the platform is unavailable, the list is served from the
    rows we already have.
    """
    stream_id = actor.stream_id
    if stream_id == models.NO_STREAM_ID or not throttle.due(stream_id):
        return
    try:
        members = platform.stream_members(stream_id)
    except Exception:
        logger.warning("Could not fetch the member list of stream %s", stream_id, exc_info=True)
        return

    known = set(
        db.scalars(select(models.User.platform_user_id).where(models.User.stream_id == stream_id))
    )
    newcomers = [_new_user_values(stream_id, m) for m in members if m.id not in known]
    if newcomers:
        db.execute(
            pg_insert(models.User)
            .values(newcomers)
            .on_conflict_do_nothing(index_elements=["stream_id", "platform_user_id"])
        )
        db.commit()


def load_board_settings(db: Session, config: Settings) -> models.BoardSettings:
    board = db.get(models.BoardSettings, 1)
    if board is None:
        db.execute(
            pg_insert(models.BoardSettings)
            .values(
                id=1,
                accept_threshold=config.default_accept_threshold,
                reject_threshold=config.default_reject_threshold,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        db.commit()
        board = db.get(models.BoardSettings, 1)
        if board is None:  # pragma: no cover
            raise RuntimeError("Board settings vanished right after creation")
    return board


# ---------------------------------------------------------------------------
# Stream-scoped lookups
# ---------------------------------------------------------------------------


def get_card(db: Session, actor: Actor, card_id: uuid.UUID) -> models.Card:
    card = db.scalar(
        select(models.Card).where(models.Card.id == card_id, models.Card.stream_id == actor.stream_id)
    )
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=CARD_NOT_FOUND)
    return card


def get_comment(db: Session, actor: Actor, comment_id: uuid.UUID) -> models.Comment:
    comment = db.scalar(
        select(models.Comment).where(
            models.Comment.id == comment_id, models.Comment.stream_id == actor.stream_id
        )
    )
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND)
    return comment


def get_member(db: Session, actor: Actor, user_id: uuid.UUID) -> models.User:
    user = db.scalar(
        select(models.User).where(models.User.id == user_id, models.User.stream_id == actor.stream_id)
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)
    return user


def members_count(db: Session, stream_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(models.User).where(models.User.stream_id == stream_id)
    ) or 0


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def unix(moment: dt.datetime) -> int:
    """The API sends every moment in time as whole Unix seconds."""
    return int(moment.timestamp())


def stream_name(stream: models.Stream) -> str:
    fallback = "Без потока" if stream.id == models.NO_STREAM_ID else "Поток"
    return stream.title or stream.code or fallback


def stream_schema(stream: models.Stream) -> schemas.Stream:
    return schemas.Stream(
        id=None if stream.id == models.NO_STREAM_ID else stream.id,
        code=stream.code,
        title=stream.title,
        name=stream_name(stream),
    )


def user_schema(user: models.User, actor: Actor) -> schemas.User:
    return schemas.User(
        id=user.id,
        name=user.name,
        avatar_url=user.avatar_url,
        status=user.status,
        bio=user.bio,
        telegram=user.telegram,
        is_me=user.id == actor.user_id,
        created_at=unix(user.created_at),
    )


def user_detail_schema(db: Session, user: models.User, actor: Actor) -> schemas.UserDetail:
    stream_id = actor.stream_id
    cards_count = db.scalar(
        select(func.count())
        .select_from(models.Card)
        .where(models.Card.stream_id == stream_id, models.Card.author_id == user.id)
    )
    comments_count = db.scalar(
        select(func.count())
        .select_from(models.Comment)
        .where(models.Comment.stream_id == stream_id, models.Comment.author_id == user.id)
    )
    total_score = db.scalar(
        select(func.coalesce(func.sum(models.Vote.value), 0))
        .select_from(models.Vote)
        .join(
            models.Card,
            (models.Card.stream_id == models.Vote.stream_id) & (models.Card.id == models.Vote.card_id),
        )
        .where(models.Vote.stream_id == stream_id, models.Card.author_id == user.id)
    )
    return schemas.UserDetail(
        **dict(user_schema(user, actor)),
        cards_count=cards_count or 0,
        comments_count=comments_count or 0,
        total_score=total_score or 0,
    )


def profile_schema(actor: Actor) -> schemas.Profile:
    user = actor.user
    return schemas.Profile(
        id=user.id,
        name=user.name,
        email=user.email,
        avatar_url=user.avatar_url,
        status=user.status,
        bio=user.bio,
        telegram=user.telegram,
        stream=stream_schema(actor.stream),
        created_at=unix(user.created_at),
        updated_at=unix(user.updated_at),
    )


def comment_schema(comment: models.Comment, actor: Actor) -> schemas.Comment:
    return schemas.Comment(
        id=comment.id,
        card_id=comment.card_id,
        text=comment.text,
        author=user_schema(comment.author, actor),
        is_mine=comment.author_id == actor.user_id,
        created_at=unix(comment.created_at),
        updated_at=unix(comment.updated_at),
    )


@dataclass
class CardCounters:
    upvotes: int = 0
    downvotes: int = 0
    comments: int = 0
    my_vote: int | None = None


def load_counters(
    db: Session, actor: Actor, card_ids: Sequence[uuid.UUID] | None = None
) -> dict[uuid.UUID, CardCounters]:
    """Votes, comment counts and the caller's own votes, in three queries for any number of cards.

    Pass `card_ids=None` to count the whole stream at once, which the board does.
    """
    Vote, Comment = models.Vote, models.Comment
    totals = (
        select(Vote.card_id, func.count().filter(Vote.value > 0), func.count().filter(Vote.value < 0))
        .where(Vote.stream_id == actor.stream_id)
        .group_by(Vote.card_id)
    )
    comments = (
        select(Comment.card_id, func.count())
        .where(Comment.stream_id == actor.stream_id)
        .group_by(Comment.card_id)
    )
    mine = select(Vote.card_id, Vote.value).where(
        Vote.stream_id == actor.stream_id, Vote.user_id == actor.user_id
    )
    if card_ids is not None:
        totals = totals.where(Vote.card_id.in_(card_ids))
        comments = comments.where(Comment.card_id.in_(card_ids))
        mine = mine.where(Vote.card_id.in_(card_ids))

    counters: dict[uuid.UUID, CardCounters] = {}
    for card_id, upvotes, downvotes in db.execute(totals):
        entry = counters.setdefault(card_id, CardCounters())
        entry.upvotes, entry.downvotes = upvotes, downvotes
    for card_id, count in db.execute(comments):
        counters.setdefault(card_id, CardCounters()).comments = count
    for card_id, value in db.execute(mine):
        counters.setdefault(card_id, CardCounters()).my_vote = value
    return counters


def card_schema(
    card: models.Card, counters: CardCounters, board: models.BoardSettings, actor: Actor
) -> schemas.Card:
    score = counters.upvotes - counters.downvotes
    is_accepted = score >= board.accept_threshold
    is_rejected = score <= -board.reject_threshold
    if is_accepted:
        column = CardColumn.accepted
    elif is_rejected:
        column = CardColumn.rejected
    else:
        column = CardColumn(card.type.value)

    my_vote = {1: VoteValue.up, -1: VoteValue.down}.get(counters.my_vote or 0)
    return schemas.Card(
        id=card.id,
        title=card.title,
        type=card.type,
        description=card.description,
        preview=card.preview,
        date=card.date,
        column=column,
        is_accepted=is_accepted,
        is_rejected=is_rejected,
        upvotes=counters.upvotes,
        downvotes=counters.downvotes,
        votes_count=counters.upvotes + counters.downvotes,
        score=score,
        votes_to_accept=max(0, board.accept_threshold - score),
        votes_to_reject=max(0, score + board.reject_threshold),
        comments_count=counters.comments,
        my_vote=my_vote,
        is_mine=card.author_id == actor.user_id,
        author=user_schema(card.author, actor),
        created_at=unix(card.created_at),
        updated_at=unix(card.updated_at),
    )


def card_schemas(
    db: Session,
    actor: Actor,
    cards: Sequence[models.Card],
    board: models.BoardSettings,
    *,
    whole_stream: bool = False,
) -> list[schemas.Card]:
    counters = load_counters(db, actor, None if whole_stream else [card.id for card in cards])
    return [card_schema(card, counters.get(card.id, CardCounters()), board, actor) for card in cards]


def single_card_schema(
    db: Session, actor: Actor, card: models.Card, board: models.BoardSettings
) -> schemas.Card:
    return card_schemas(db, actor, [card], board)[0]


def comment_schemas(db: Session, actor: Actor, card: models.Card) -> list[schemas.Comment]:
    """A card's comments, oldest first."""
    comments = db.scalars(
        select(models.Comment)
        .where(models.Comment.stream_id == actor.stream_id, models.Comment.card_id == card.id)
        .order_by(models.Comment.created_at, models.Comment.id)
    ).all()
    return [comment_schema(comment, actor) for comment in comments]


def card_detail_schema(
    db: Session, actor: Actor, card: models.Card, board: models.BoardSettings
) -> schemas.CardDetail:
    return schemas.CardDetail(
        **dict(single_card_schema(db, actor, card, board)),
        comments=comment_schemas(db, actor, card),
    )


def list_card_schemas(
    db: Session,
    actor: Actor,
    board: models.BoardSettings,
    *,
    column: CardColumn | None = None,
    card_type: CardType | None = None,
    author_id: uuid.UUID | None = None,
    search: str | None = None,
    sort: CardSort = CardSort.new,
) -> list[schemas.Card]:
    Card = models.Card
    query = select(Card).where(Card.stream_id == actor.stream_id)
    if card_type is not None:
        query = query.where(Card.type == card_type)
    if author_id is not None:
        query = query.where(Card.author_id == author_id)
    if search:
        query = query.where(
            or_(
                Card.title.icontains(search, autoescape=True),
                Card.description.icontains(search, autoescape=True),
            )
        )
    if sort == CardSort.old:
        query = query.order_by(Card.created_at, Card.id)
    else:
        query = query.order_by(Card.created_at.desc(), Card.id.desc())

    views = card_schemas(db, actor, db.scalars(query).all(), board, whole_stream=True)
    # `column` depends on live scores, so it is filtered after counting.
    if column is not None:
        views = [view for view in views if view.column == column]
    if sort == CardSort.top:
        views.sort(key=lambda view: view.score, reverse=True)  # stable: ties stay newest first
    return views
