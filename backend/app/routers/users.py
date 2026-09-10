"""Your profile and the other members of your stream."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Query, Request, status
from sqlalchemy import func, select

from app import models, schemas, services
from app.deps import CurrentActor, DbSession
from app.docs import AUTH_ERRORS, EMAIL_CONFLICT, EMAIL_TAKEN, EMAIL_TAKEN_DETAIL, VALIDATION_ERROR, not_found
from app.errors import FieldProblem
from app.services import USER_NOT_FOUND

router = APIRouter()

PROFILE_EXAMPLES: dict[str, Any] = {
    "status": {"summary": "Поставить статус", "value": {"status": "Ищу команду на хакатон"}},
    "full": {
        "summary": "Заполнить весь профиль",
        "value": {
            "name": "Аня Петрова",
            "email": "anya@example.com",
            "avatar_url": "https://i.pravatar.cc/150?img=5",
            "status": "Учу React по вечерам",
            "bio": "Люблю аккуратную вёрстку и котиков.",
            "telegram": "@anya_codes",
        },
    },
    "clear": {"summary": "Убрать аватар и статус", "value": {"avatar_url": None, "status": None}},
}


@router.get("/me", response_model=schemas.Profile, tags=["Profile"], summary="Ваш профиль", responses=AUTH_ERRORS)
def get_me(actor: CurrentActor) -> schemas.Profile:
    """Кто вы в этом API, включая ваш личный `email` и `stream`.

    Самый первый запрос создаёт профиль из вашего профиля на платформе курса (имя, email и
    аватар). После этого он ваш: меняйте его через `PATCH /api/me`.
    """
    return services.profile_schema(actor)


@router.patch(
    "/me",
    response_model=schemas.Profile,
    tags=["Profile"],
    summary="Изменить профиль",
    responses={**AUTH_ERRORS, 409: EMAIL_CONFLICT, 422: VALIDATION_ERROR},
)
def update_me(
    body: Annotated[schemas.ProfileUpdate, Body(openapi_examples=PROFILE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
) -> schemas.Profile:
    """Изменяет ваш профиль. Отправляйте только поля, которые хотите поменять.

    Сервер проверяет всё, так что это хороший ориентир для валидации в вашей форме:

    - `name`: 1-80 символов, очистить нельзя.
    - `email`: корректный адрес, которым не пользуется другой участник (иначе **409** с
      `errors: [{"field": "email", "message": "Этот email уже занят"}]`).
    - `avatar_url`: ссылка на картинку http(s) или `data:image/...` URI.
    - `telegram`: 5-32 латинских буквы, цифры или подчёркивания; `@` необязателен.
    - `status` — до 100 символов, `bio` — до 1000.

    Ничего из этого не меняет ваш профиль на платформе курса.
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
                status.HTTP_409_CONFLICT, field="email", message=EMAIL_TAKEN, detail=EMAIL_TAKEN_DETAIL
            )
    for field, value in changes.items():
        setattr(actor.user, field, value)
    db.commit()
    return services.profile_schema(actor)


@router.get(
    "/users",
    response_model=list[schemas.User],
    tags=["People"],
    summary="Участники доски",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def list_users(
    request: Request,
    actor: CurrentActor,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=80, description="Поиск по имени без учёта регистра.")] = None,
) -> list[schemas.User]:
    """Все участники доски, по алфавиту.

    В списке есть и однокурсники, которые ещё не обращались к API. Они показываются с именем и
    аватаром с платформы курса, пока не изменят профиль здесь.
    """
    state = request.app.state
    services.sync_roster(db, actor, state.platform, state.roster_throttle)

    query = select(models.User).where(models.User.stream_id == actor.stream_id)
    if q:
        query = query.where(models.User.name.icontains(q, autoescape=True))
    users = db.scalars(query.order_by(func.lower(models.User.name), models.User.id)).all()
    return [services.user_schema(user, actor) for user in users]


@router.get(
    "/users/{user_id}",
    response_model=schemas.UserDetail,
    tags=["People"],
    summary="Один участник со счётчиками активности",
    responses={**AUTH_ERRORS, 404: not_found(USER_NOT_FOUND)},
)
def get_user(
    user_id: Annotated[uuid.UUID, Path(description="Id пользователя, например `card.author.id`.")],
    actor: CurrentActor,
    db: DbSession,
) -> schemas.UserDetail:
    """Публичный профиль участника плюс `cards_count`, `comments_count` и `total_score` — для
    страницы пользователя. Его карточки: `GET /api/cards?author_id={user_id}`."""
    user = services.get_member(db, actor, user_id)
    return services.user_detail_schema(db, user, actor)
