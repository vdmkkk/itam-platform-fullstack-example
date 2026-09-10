"""Your profile and the other members of your stream."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Query, Request, status
from sqlalchemy import func, select

from app import models, schemas, services
from app.deps import CurrentActor, DbSession
from app.docs import AUTH_ERRORS, EMAIL_CONFLICT, VALIDATION_ERROR, not_found
from app.errors import FieldProblem

router = APIRouter()

PROFILE_EXAMPLES: dict[str, Any] = {
    "status": {"summary": "Set a status", "value": {"status": "Ищу команду на хакатон"}},
    "full": {
        "summary": "Fill in the whole profile",
        "value": {
            "name": "Аня Петрова",
            "email": "anya@example.com",
            "avatar_url": "https://i.pravatar.cc/150?img=5",
            "status": "Учу React по вечерам",
            "bio": "Люблю аккуратную вёрстку и котиков.",
            "telegram": "@anya_codes",
        },
    },
    "clear": {"summary": "Clear the avatar and the status", "value": {"avatar_url": None, "status": None}},
}


@router.get("/me", response_model=schemas.Profile, tags=["Profile"], summary="Your profile", responses=AUTH_ERRORS)
def get_me(actor: CurrentActor) -> schemas.Profile:
    """Who you are in this API, including your private `email` and your `stream`.

    Your very first request creates the profile from your course platform profile (name,
    email and avatar). After that it's yours to change with `PATCH /api/me`.
    """
    return services.profile_schema(actor)


@router.patch(
    "/me",
    response_model=schemas.Profile,
    tags=["Profile"],
    summary="Edit your profile",
    responses={**AUTH_ERRORS, 409: EMAIL_CONFLICT, 422: VALIDATION_ERROR},
)
def update_me(
    body: Annotated[schemas.ProfileUpdate, Body(openapi_examples=PROFILE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
) -> schemas.Profile:
    """Change your profile. Send only the fields you want to change.

    The server validates everything, a good match for client-side validation in your form:

    - `name`: 1-80 characters. It can't be cleared.
    - `email`: a valid address, not used by anyone else in your stream (otherwise **409**
      with `errors: [{"field": "email", "message": "This email is already in use"}]`).
    - `avatar_url`: an http(s) image link or a `data:image/...` URI.
    - `telegram`: 5-32 letters, digits or underscores. The `@` is optional.
    - `status` up to 100 characters, `bio` up to 1000.

    None of this changes your course platform profile.
    """
    changes = body.model_dump(exclude_unset=True)
    email = changes.get("email")
    if email:
        taken = db.scalar(
            select(models.User.id)
            .where(
                models.User.stream_id == actor.stream_id,
                func.lower(models.User.email) == email.lower(),
                models.User.id != actor.user_id,
            )
            .limit(1)
        )
        if taken is not None:
            raise FieldProblem(
                status.HTTP_409_CONFLICT,
                field="email",
                message="This email is already in use",
                detail="This email is already in use by another member of your stream.",
            )
    for field, value in changes.items():
        setattr(actor.user, field, value)
    db.commit()
    return services.profile_schema(actor)


@router.get(
    "/users",
    response_model=list[schemas.User],
    tags=["People"],
    summary="Members of your stream",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def list_users(
    request: Request,
    actor: CurrentActor,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=80, description="Case-insensitive search by name.")] = None,
    include_demo: Annotated[
        bool, Query(description="Include the demo people who fill new boards with examples.")
    ] = True,
) -> list[schemas.User]:
    """Everyone in your stream: real people first, sorted by name, then the demo people.

    The list includes classmates who haven't used the API yet. They appear with their course
    platform name and avatar until they edit their profile here.
    """
    state = request.app.state
    services.sync_roster(db, actor, state.platform, state.roster_throttle)

    query = select(models.User).where(models.User.stream_id == actor.stream_id)
    if q:
        query = query.where(models.User.name.icontains(q, autoescape=True))
    if not include_demo:
        query = query.where(models.User.is_demo.is_(False))
    users = db.scalars(query.order_by(models.User.is_demo, func.lower(models.User.name))).all()
    return [services.user_schema(user, actor) for user in users]


@router.get(
    "/users/{user_id}",
    response_model=schemas.UserDetail,
    tags=["People"],
    summary="One member, with activity counters",
    responses={**AUTH_ERRORS, 404: not_found("User not found in your stream.")},
)
def get_user(
    user_id: Annotated[uuid.UUID, Path(description="User id, e.g. `card.author.id`.")],
    actor: CurrentActor,
    db: DbSession,
) -> schemas.UserDetail:
    """A member's public profile plus `cards_count`, `comments_count` and `total_score`, for a
    user page. Get their cards with `GET /api/cards?author_id={user_id}`."""
    user = services.get_member(db, actor, user_id)
    return services.user_detail_schema(db, user, actor)
