"""Cards, the votes on them, and the comments on them."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status
from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import models, schemas, services
from app.deps import BoardThresholds, CurrentActor, DbSession
from app.docs import AUTH_ERRORS, VALIDATION_ERROR, forbidden, not_found
from app.enums import CardColumn, CardSort, CardType, VoteValue

router = APIRouter()

CardId = Annotated[uuid.UUID, Path(description="Card id.")]
CARD_NOT_FOUND = "Card not found. It may have been deleted."

CREATE_EXAMPLES: dict[str, Any] = {
    "idea": {
        "summary": "An idea (only the required fields)",
        "value": {"title": "Добавить тёмную тему", "type": "idea"},
    },
    "event": {
        "summary": "An event with a description, a date and a picture",
        "value": {
            "title": "Хакатон ITAM",
            "type": "event",
            "description": "Собираем команды по 3–4 человека.",
            "date": "2026-10-10",
            "preview": "https://picsum.photos/seed/hackathon/640/360",
        },
    },
    "question": {
        "summary": "A question",
        "value": {
            "title": "Где лучше хранить токен во фронтенде?",
            "type": "question",
            "description": "В .env или прямо в коде?",
        },
    },
}

UPDATE_EXAMPLES: dict[str, Any] = {
    "rename": {"summary": "Change the title", "value": {"title": "Хакатон ITAM: ищем дизайнера"}},
    "retype": {"summary": "Move to another column (change the type)", "value": {"type": "event"}},
    "clear": {"summary": "Remove the picture and the date", "value": {"preview": None, "date": None}},
}

VOTE_EXAMPLES: dict[str, Any] = {
    "up": {"summary": "Upvote", "value": {"value": "up"}},
    "down": {"summary": "Downvote", "value": {"value": "down"}},
}


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------


@router.get(
    "/cards",
    response_model=list[schemas.Card],
    tags=["Cards"],
    summary="All cards on the board",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def list_cards(
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
    column: Annotated[
        CardColumn | None, Query(description="Only cards that are in this column right now.")
    ] = None,
    type: Annotated[
        CardType | None,
        Query(description="Only cards of this type. Accepted and rejected cards keep their type."),
    ] = None,
    author_id: Annotated[
        uuid.UUID | None,
        Query(description='Only cards by this user. Use your own id from `GET /api/me` for "my cards".'),
    ] = None,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Case-insensitive search in the title and description."),
    ] = None,
    sort: Annotated[CardSort, Query(description="Order of the list.")] = CardSort.new,
) -> list[schemas.Card]:
    """Every card on your stream's board, with everything needed to draw it: votes, score,
    your own vote (`my_vote`), the comment count and the author.

    **To render the board**, call this without filters and group the cards by `card.column`.

    All filters are optional and can be combined. They are handy in Swagger, or for a user
    page (`author_id`).
    """
    return services.list_card_schemas(
        db, actor, board, column=column, card_type=type, author_id=author_id, search=q, sort=sort
    )


@router.post(
    "/cards",
    response_model=schemas.Card,
    status_code=status.HTTP_201_CREATED,
    tags=["Cards"],
    summary="Create a card",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def create_card(
    body: Annotated[schemas.CardCreate, Body(openapi_examples=CREATE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
) -> schemas.Card:
    """Post a new card as yourself. Only `title` and `type` are required.

    `type` is `event`, `idea` or `question`. Only votes can move a card to
    *accepted* or *rejected*.

    It answers `201 Created` with the new card, the same shape as in `GET /api/cards`, so you
    can add it straight to your state.
    """
    card = models.Card(stream_id=actor.stream_id, author_id=actor.user_id, **body.model_dump())
    db.add(card)
    db.commit()
    return services.single_card_schema(db, actor, card, board)


@router.get(
    "/cards/{card_id}",
    response_model=schemas.CardDetail,
    tags=["Cards"],
    summary="One card with its comments",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def get_card(card_id: CardId, actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.CardDetail:
    """The same fields as in the list, plus `comments`: all of them, oldest first, each with
    its author. Use it for a card page or modal."""
    card = services.get_card(db, actor, card_id)
    return services.card_detail_schema(db, actor, card, board)


@router.patch(
    "/cards/{card_id}",
    response_model=schemas.Card,
    tags=["Cards"],
    summary="Edit your card",
    responses={
        **AUTH_ERRORS,
        403: forbidden("Only the author can edit this card."),
        404: not_found(CARD_NOT_FOUND),
        422: VALIDATION_ERROR,
    },
)
def update_card(
    card_id: CardId,
    body: Annotated[schemas.CardUpdate, Body(openapi_examples=UPDATE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
) -> schemas.Card:
    """Change **your own** card. Send only the fields you want to change. Omitted fields stay
    as they are, and `null` clears `description`, `preview` or `date`.

    Changing `type` moves the card between the event, idea and question columns. Votes stay
    as they are, so an accepted card stays accepted.
    """
    card = services.get_card(db, actor, card_id)
    if card.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the author can edit this card.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(card, field, value)
    db.commit()
    return services.single_card_schema(db, actor, card, board)


@router.delete(
    "/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["Cards"],
    summary="Delete your card",
    responses={
        **AUTH_ERRORS,
        403: forbidden("Only the author can delete this card."),
        404: not_found(CARD_NOT_FOUND),
    },
)
def delete_card(card_id: CardId, actor: CurrentActor, db: DbSession) -> Response:
    """Delete **your own** card together with its votes and comments. It answers
    `204 No Content` with an **empty body**, so don't call `response.json()` on it."""
    card = services.get_card(db, actor, card_id)
    if card.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the author can delete this card.")
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


@router.put(
    "/cards/{card_id}/vote",
    response_model=schemas.Card,
    tags=["Votes"],
    summary="Vote on a card (up or down)",
    responses={
        **AUTH_ERRORS,
        403: forbidden("You can't vote on your own card."),
        404: not_found(CARD_NOT_FOUND),
        422: VALIDATION_ERROR,
    },
)
def vote_card(
    card_id: CardId,
    body: Annotated[schemas.VoteRequest, Body(openapi_examples=VOTE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
) -> schemas.Card:
    """Set your vote on someone else's card. You get **one vote per card**:

    - voting `up` when you already voted `down` changes your vote, so the score moves by 2;
    - sending the same vote again changes nothing (it's safe to repeat);
    - voting on your own card gives 403.

    It answers with the updated card, so you can replace it in your state. If its score reaches
    a threshold, its `column` is already `accepted` or `rejected`.
    """
    card = services.get_card(db, actor, card_id)
    if card.author_id == actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You can't vote on your own card.")
    value = 1 if body.value == VoteValue.up else -1
    db.execute(
        pg_insert(models.Vote)
        .values(card_id=card.id, user_id=actor.user_id, stream_id=actor.stream_id, value=value)
        .on_conflict_do_update(
            index_elements=["card_id", "user_id"], set_={"value": value, "updated_at": func.now()}
        )
    )
    db.commit()
    return services.single_card_schema(db, actor, card, board)


@router.delete(
    "/cards/{card_id}/vote",
    response_model=schemas.Card,
    tags=["Votes"],
    summary="Remove your vote",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def remove_vote(card_id: CardId, actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.Card:
    """Take your vote back. If you hadn't voted, nothing happens. Either way it answers with the
    updated card (with `my_vote: null`)."""
    card = services.get_card(db, actor, card_id)
    db.execute(
        delete(models.Vote).where(
            models.Vote.stream_id == actor.stream_id,
            models.Vote.card_id == card.id,
            models.Vote.user_id == actor.user_id,
        )
    )
    db.commit()
    return services.single_card_schema(db, actor, card, board)


# ---------------------------------------------------------------------------
# Comments on a card
# ---------------------------------------------------------------------------


@router.get(
    "/cards/{card_id}/comments",
    response_model=list[schemas.Comment],
    tags=["Comments"],
    summary="Comments on a card",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def list_card_comments(card_id: CardId, actor: CurrentActor, db: DbSession) -> list[schemas.Comment]:
    """All comments on the card, oldest first. `GET /api/cards/{card_id}` includes them too."""
    card = services.get_card(db, actor, card_id)
    return services.comment_schemas(db, actor, card)


@router.post(
    "/cards/{card_id}/comments",
    response_model=schemas.Comment,
    status_code=status.HTTP_201_CREATED,
    tags=["Comments"],
    summary="Comment on a card",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND), 422: VALIDATION_ERROR},
)
def create_comment(
    card_id: CardId, body: schemas.CommentCreate, actor: CurrentActor, db: DbSession
) -> schemas.Comment:
    """Write a comment on any card in your stream, your own included. Comments are flat, so
    there are no replies to comments. It answers `201 Created` with the new comment."""
    card = services.get_card(db, actor, card_id)
    comment = models.Comment(
        stream_id=actor.stream_id, card_id=card.id, author_id=actor.user_id, text=body.text
    )
    db.add(comment)
    db.commit()
    return services.comment_schema(comment, actor)
