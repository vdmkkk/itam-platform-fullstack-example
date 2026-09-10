"""Course-team tools. Every endpoint requires the `X-Admin-Token` header."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import func, select

from app import models, schemas, services
from app.deps import BoardThresholds, DbSession, require_admin
from app.docs import ADMIN_ERRORS, VALIDATION_ERROR, not_found

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


def _settings_schema(board: models.BoardSettings) -> schemas.BoardSettings:
    return schemas.BoardSettings(
        accept_threshold=board.accept_threshold,
        reject_threshold=board.reject_threshold,
        updated_at=board.updated_at,
    )


@router.get("/settings", response_model=schemas.BoardSettings, summary="Read the vote thresholds", responses=ADMIN_ERRORS)
def get_settings(board: BoardThresholds) -> schemas.BoardSettings:
    """The current thresholds, shared by all streams."""
    return _settings_schema(board)


@router.patch(
    "/settings",
    response_model=schemas.BoardSettings,
    summary="Change the vote thresholds",
    responses={**ADMIN_ERRORS, 422: VALIDATION_ERROR},
)
def update_settings(
    body: schemas.BoardSettingsUpdate, db: DbSession, board: BoardThresholds
) -> schemas.BoardSettings:
    """Set `accept_threshold` and/or `reject_threshold`.

    Acceptance is computed live, so the change applies **immediately to every existing card
    in every stream**. Lowering the accept threshold can move many cards to *accepted* at once.
    """
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(board, field, value)
    db.commit()
    return _settings_schema(board)


def _count_by_stream(db: DbSession, model: Any, *conditions: Any) -> dict[uuid.UUID, int]:
    query = select(model.stream_id, func.count()).group_by(model.stream_id)
    if conditions:
        query = query.where(*conditions)
    return {stream_id: count for stream_id, count in db.execute(query)}


@router.get("/streams", response_model=list[schemas.AdminStream], summary="Streams and their activity", responses=ADMIN_ERRORS)
def list_streams(db: DbSession) -> list[schemas.AdminStream]:
    """Every stream that has used the API, oldest first, with activity counters."""
    members = _count_by_stream(db, models.User, models.User.is_demo.is_(False))
    cards = _count_by_stream(db, models.Card)
    comments = _count_by_stream(db, models.Comment)
    votes = _count_by_stream(db, models.Vote)
    streams = db.scalars(select(models.Stream).order_by(models.Stream.created_at)).all()
    return [
        schemas.AdminStream(
            id=None if stream.id == models.NO_STREAM_ID else stream.id,
            code=stream.code,
            title=stream.title,
            name=services.stream_name(stream),
            members_count=members.get(stream.id, 0),
            cards_count=cards.get(stream.id, 0),
            comments_count=comments.get(stream.id, 0),
            votes_count=votes.get(stream.id, 0),
            first_seen_at=stream.created_at,
        )
        for stream in streams
    ]


@router.delete(
    "/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove any card (moderation)",
    responses={**ADMIN_ERRORS, 404: not_found("Card not found.")},
)
def admin_delete_card(
    card_id: Annotated[uuid.UUID, Path(description="Card id.")], db: DbSession
) -> Response:
    """Delete a card from any stream, with its votes and comments."""
    card = db.get(models.Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found.")
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove any comment (moderation)",
    responses={**ADMIN_ERRORS, 404: not_found("Comment not found.")},
)
def admin_delete_comment(
    comment_id: Annotated[uuid.UUID, Path(description="Comment id.")], db: DbSession
) -> Response:
    """Delete a comment from any stream."""
    comment = db.get(models.Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
