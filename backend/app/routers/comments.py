"""Editing and deleting comments.

Listing and creating them lives on the card: `GET/POST /api/cards/{card_id}/comments`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from app import schemas, services
from app.deps import CurrentActor, DbSession
from app.docs import AUTH_ERRORS, VALIDATION_ERROR, forbidden, not_found
from app.services import COMMENT_NOT_FOUND

router = APIRouter(tags=["Comments"])

CommentId = Annotated[uuid.UUID, Path(description="Id комментария.")]
ONLY_AUTHOR_EDITS = "Изменить комментарий может только его автор."
ONLY_AUTHOR_DELETES = "Удалить комментарий может только его автор."


@router.patch(
    "/comments/{comment_id}",
    response_model=schemas.Comment,
    summary="Изменить свой комментарий",
    responses={
        **AUTH_ERRORS,
        403: forbidden(ONLY_AUTHOR_EDITS),
        404: not_found(COMMENT_NOT_FOUND),
        422: VALIDATION_ERROR,
    },
)
def update_comment(
    comment_id: CommentId, body: schemas.CommentUpdate, actor: CurrentActor, db: DbSession
) -> schemas.Comment:
    """Заменяет текст **вашего** комментария. Его `updated_at` меняется, так что можно
    показывать «(изменено)», когда `updated_at` отличается от `created_at`."""
    comment = services.get_comment(db, actor, comment_id)
    if comment.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ONLY_AUTHOR_EDITS)
    comment.text = body.text
    db.commit()
    return services.comment_schema(comment, actor)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Удалить свой комментарий",
    responses={
        **AUTH_ERRORS,
        403: forbidden(ONLY_AUTHOR_DELETES),
        404: not_found(COMMENT_NOT_FOUND),
    },
)
def delete_comment(comment_id: CommentId, actor: CurrentActor, db: DbSession) -> Response:
    """Удаляет **ваш** комментарий. Ответ — `204 No Content` с пустым телом."""
    comment = services.get_comment(db, actor, comment_id)
    if comment.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ONLY_AUTHOR_DELETES)
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
