"""Course-team tools. Every endpoint requires the `X-Admin-Token` header."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import func, select

from app import models, schemas, services
from app.deps import BoardThresholds, DbSession, require_admin
from app.docs import ADMIN_ERRORS, VALIDATION_ERROR, not_found
from app.services import CARD_NOT_FOUND, COMMENT_NOT_FOUND

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


def _settings_schema(board: models.BoardSettings) -> schemas.BoardSettings:
    return schemas.BoardSettings(
        accept_threshold=board.accept_threshold,
        reject_threshold=board.reject_threshold,
        updated_at=board.updated_at,
    )


@router.get("/settings", response_model=schemas.BoardSettings, summary="Текущие пороги голосования", responses=ADMIN_ERRORS)
def get_settings(board: BoardThresholds) -> schemas.BoardSettings:
    """Текущие пороги, общие для всех потоков."""
    return _settings_schema(board)


@router.patch(
    "/settings",
    response_model=schemas.BoardSettings,
    summary="Изменить пороги голосования",
    responses={**ADMIN_ERRORS, 422: VALIDATION_ERROR},
)
def update_settings(
    body: schemas.BoardSettingsUpdate, db: DbSession, board: BoardThresholds
) -> schemas.BoardSettings:
    """Задаёт `accept_threshold` и/или `reject_threshold`.

    Принятие считается на лету, поэтому изменение **сразу применяется ко всем карточкам во всех
    потоках**. Если снизить порог принятия, много карточек может сразу оказаться в *accepted*.
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


@router.get("/streams", response_model=list[schemas.AdminStream], summary="Потоки и их активность", responses=ADMIN_ERRORS)
def list_streams(db: DbSession) -> list[schemas.AdminStream]:
    """Все потоки, которые обращались к API, от старых к новым, со счётчиками активности."""
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
    summary="Удалить любую карточку (модерация)",
    responses={**ADMIN_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def admin_delete_card(
    card_id: Annotated[uuid.UUID, Path(description="Id карточки.")], db: DbSession
) -> Response:
    """Удаляет карточку из любого потока вместе с её голосами и комментариями."""
    card = db.get(models.Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=CARD_NOT_FOUND)
    db.delete(card)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Удалить любой комментарий (модерация)",
    responses={**ADMIN_ERRORS, 404: not_found(COMMENT_NOT_FOUND)},
)
def admin_delete_comment(
    comment_id: Annotated[uuid.UUID, Path(description="Id комментария.")], db: DbSession
) -> Response:
    """Удаляет комментарий из любого потока."""
    comment = db.get(models.Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND)
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
