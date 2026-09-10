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
from app.schemas import EXAMPLE_UNIX_TIME
from app.services import CARD_NOT_FOUND

router = APIRouter()

CardId = Annotated[uuid.UUID, Path(description="Id карточки.")]
ONLY_AUTHOR_EDITS = "Изменить карточку может только её автор."
ONLY_AUTHOR_DELETES = "Удалить карточку может только её автор."
NO_SELF_VOTE = "Нельзя голосовать за свою карточку."

CREATE_EXAMPLES: dict[str, Any] = {
    "idea": {
        "summary": "Идея (только обязательные поля)",
        "value": {"title": "Добавить тёмную тему", "type": "idea"},
    },
    "event": {
        "summary": "Событие с описанием, датой и картинкой",
        "value": {
            "title": "Хакатон ITAM",
            "type": "event",
            "description": "Собираем команды по 3–4 человека.",
            "date": EXAMPLE_UNIX_TIME,
            "preview": "https://picsum.photos/seed/hackathon/640/360",
        },
    },
    "question": {
        "summary": "Вопрос",
        "value": {
            "title": "Где лучше хранить токен во фронтенде?",
            "type": "question",
            "description": "В .env или прямо в коде?",
        },
    },
}

UPDATE_EXAMPLES: dict[str, Any] = {
    "rename": {"summary": "Поменять заголовок", "value": {"title": "Хакатон ITAM: ищем дизайнера"}},
    "retype": {"summary": "Перенести в другую колонку (сменить тип)", "value": {"type": "event"}},
    "redate": {"summary": "Перенести дату", "value": {"date": EXAMPLE_UNIX_TIME + 86400}},
    "clear": {"summary": "Убрать картинку и дату", "value": {"preview": None, "date": None}},
}

VOTE_EXAMPLES: dict[str, Any] = {
    "up": {"summary": "Голос «за»", "value": {"value": "up"}},
    "down": {"summary": "Голос «против»", "value": {"value": "down"}},
}


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------


@router.get(
    "/cards",
    response_model=list[schemas.Card],
    tags=["Cards"],
    summary="Все карточки доски",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def list_cards(
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
    column: Annotated[
        CardColumn | None, Query(description="Только карточки, которые сейчас в этой колонке.")
    ] = None,
    type: Annotated[
        CardType | None,
        Query(description="Только карточки этого типа. Принятые и отклонённые карточки сохраняют свой тип."),
    ] = None,
    author_id: Annotated[
        uuid.UUID | None,
        Query(description="Только карточки этого пользователя. Для «моих карточек» возьмите свой id из `GET /api/me`."),
    ] = None,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Поиск по заголовку и описанию без учёта регистра."),
    ] = None,
    sort: Annotated[CardSort, Query(description="Порядок списка.")] = CardSort.new,
) -> list[schemas.Card]:
    """Все карточки доски со всем, что нужно для отрисовки: голоса, счёт, ваш голос
    (`my_vote`), число комментариев и автор.

    **Чтобы нарисовать доску**, вызовите без фильтров и сгруппируйте карточки по `card.column`.

    Все фильтры необязательные и сочетаются друг с другом. Они удобны в Swagger или для
    страницы пользователя (`author_id`).
    """
    return services.list_card_schemas(
        db, actor, board, column=column, card_type=type, author_id=author_id, search=q, sort=sort
    )


@router.post(
    "/cards",
    response_model=schemas.Card,
    status_code=status.HTTP_201_CREATED,
    tags=["Cards"],
    summary="Создать карточку",
    responses={**AUTH_ERRORS, 422: VALIDATION_ERROR},
)
def create_card(
    body: Annotated[schemas.CardCreate, Body(openapi_examples=CREATE_EXAMPLES)],
    actor: CurrentActor,
    db: DbSession,
    board: BoardThresholds,
) -> schemas.Card:
    """Публикует новую карточку от вашего имени. Обязательны только `title` и `type`.

    `type` — `event`, `idea` или `question`. В *accepted* и *rejected* карточку переносят
    только голоса. `date` — Unix-время в секундах.

    Ответ — `201 Created` с новой карточкой в том же формате, что и в `GET /api/cards`, так что
    её можно сразу добавить в состояние.
    """
    card = models.Card(stream_id=actor.stream_id, author_id=actor.user_id, **body.model_dump())
    db.add(card)
    db.commit()
    return services.single_card_schema(db, actor, card, board)


@router.get(
    "/cards/{card_id}",
    response_model=schemas.CardDetail,
    tags=["Cards"],
    summary="Одна карточка с комментариями",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def get_card(card_id: CardId, actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.CardDetail:
    """Те же поля, что и в списке, плюс `comments`: все комментарии, от старых к новым, каждый
    со своим автором. Подходит для страницы или модального окна карточки."""
    card = services.get_card(db, actor, card_id)
    return services.card_detail_schema(db, actor, card, board)


@router.patch(
    "/cards/{card_id}",
    response_model=schemas.Card,
    tags=["Cards"],
    summary="Изменить свою карточку",
    responses={
        **AUTH_ERRORS,
        403: forbidden(ONLY_AUTHOR_EDITS),
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
    """Изменяет **вашу** карточку. Отправляйте только поля, которые хотите поменять:
    пропущенные останутся как есть, а `null` очищает `description`, `preview` или `date`.

    Смена `type` переносит карточку между колонками event, idea и question. Голоса при этом не
    меняются, так что принятая карточка останется принятой.
    """
    card = services.get_card(db, actor, card_id)
    if card.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ONLY_AUTHOR_EDITS)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(card, field, value)
    db.commit()
    return services.single_card_schema(db, actor, card, board)


@router.delete(
    "/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["Cards"],
    summary="Удалить свою карточку",
    responses={
        **AUTH_ERRORS,
        403: forbidden(ONLY_AUTHOR_DELETES),
        404: not_found(CARD_NOT_FOUND),
    },
)
def delete_card(card_id: CardId, actor: CurrentActor, db: DbSession) -> Response:
    """Удаляет **вашу** карточку вместе с её голосами и комментариями. Ответ —
    `204 No Content` с **пустым телом**, так что не вызывайте на нём `response.json()`."""
    card = services.get_card(db, actor, card_id)
    if card.author_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ONLY_AUTHOR_DELETES)
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
    summary="Проголосовать за карточку (за или против)",
    responses={
        **AUTH_ERRORS,
        403: forbidden(NO_SELF_VOTE),
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
    """Ставит ваш голос на чужую карточку. У вас **один голос на карточку**:

    - голос `up` поверх вашего `down` меняет голос, и счёт сдвигается на 2;
    - повтор того же голоса ничего не меняет (повторять безопасно);
    - голос за свою карточку — 403.

    Ответ — обновлённая карточка, её можно сразу заменить в состоянии. Если счёт дошёл до
    порога, её `column` уже `accepted` или `rejected`.
    """
    card = services.get_card(db, actor, card_id)
    if card.author_id == actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NO_SELF_VOTE)
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
    summary="Отозвать свой голос",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def remove_vote(card_id: CardId, actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.Card:
    """Забирает ваш голос. Если вы не голосовали, ничего не произойдёт. В любом случае ответ —
    обновлённая карточка (с `my_vote: null`)."""
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
    summary="Комментарии к карточке",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND)},
)
def list_card_comments(card_id: CardId, actor: CurrentActor, db: DbSession) -> list[schemas.Comment]:
    """Все комментарии к карточке, от старых к новым. Они же есть в `GET /api/cards/{card_id}`."""
    card = services.get_card(db, actor, card_id)
    return services.comment_schemas(db, actor, card)


@router.post(
    "/cards/{card_id}/comments",
    response_model=schemas.Comment,
    status_code=status.HTTP_201_CREATED,
    tags=["Comments"],
    summary="Прокомментировать карточку",
    responses={**AUTH_ERRORS, 404: not_found(CARD_NOT_FOUND), 422: VALIDATION_ERROR},
)
def create_comment(
    card_id: CardId, body: schemas.CommentCreate, actor: CurrentActor, db: DbSession
) -> schemas.Comment:
    """Добавляет комментарий к любой карточке на доске, включая ваши. Комментарии плоские:
    отвечать на комментарии нельзя. Ответ — `201 Created` с новым комментарием."""
    card = services.get_card(db, actor, card_id)
    comment = models.Comment(
        stream_id=actor.stream_id, card_id=card.id, author_id=actor.user_id, text=body.text
    )
    db.add(comment)
    db.commit()
    return services.comment_schema(comment, actor)
