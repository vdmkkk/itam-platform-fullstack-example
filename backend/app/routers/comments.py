"""Editing and deleting comments.

Listing and creating them lives on the card: `GET/POST /api/cards/{card_id}/comments`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from app import schemas, services
from app.deps import CurrentActor, DbSession
from app.docs import AUTH_ERRORS, VALIDATION_ERROR, forbidden, not_found

router = APIRouter(tags=["Comments"])

CommentId = Annotated[uuid.UUID, Path(description="Comment id.")]
COMMENT_NOT_FOUND = "Comment not found. It may have been deleted."


@router.patch(
    "/comments/{comment_id}",
    response_model=schemas.Comment,
    summary="Edit your comment",
    responses={
        **AUTH_ERRORS,
        403: forbidden("Only the author can edit this comment."),
        404: not_found(COMMENT_NOT_FOUND),
        422: VALIDATION_ERROR,
    },
)
def update_comment(
    comment_id: CommentId, body: schemas.CommentUpdate, actor: CurrentActor, db: DbSession
) -> schemas.Comment:
    """Replace the text of **your own** comment. Its `updated_at` changes, so you can show
    "(edited)" when `updated_at` differs from `created_at`."""
    comment = services.get_comment(db, actor, comment_id)
    if comment.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the author can edit this comment.")
    comment.text = body.text
    db.commit()
    return services.comment_schema(comment, actor)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete your comment",
    responses={
        **AUTH_ERRORS,
        403: forbidden("Only the author can delete this comment."),
        404: not_found(COMMENT_NOT_FOUND),
    },
)
def delete_comment(comment_id: CommentId, actor: CurrentActor, db: DbSession) -> Response:
    """Delete **your own** comment. It answers `204 No Content` with an empty body."""
    comment = services.get_comment(db, actor, comment_id)
    if comment.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the author can delete this comment.")
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
