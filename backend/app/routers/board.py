from collections import Counter

from fastapi import APIRouter

from app import schemas, services
from app.deps import BoardThresholds, CurrentActor, DbSession
from app.docs import AUTH_ERRORS

router = APIRouter(tags=["Board"])


@router.get(
    "/board",
    response_model=schemas.Board,
    summary="Обзор доски: колонки и пороги голосования",
    responses=AUTH_ERRORS,
)
def get_board(actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.Board:
    """Всё о доске, **кроме** самих карточек:

    - `accept_threshold` / `reject_threshold`: сколько голосов в сумме переносят карточку в
      *accepted* / *rejected*;
    - `columns`: все пять колонок в порядке отображения и сколько карточек в каждой прямо сейчас;
    - `stream`: поток курса, которому принадлежит доска.

    Потом загрузите карточки через `GET /api/cards` и сгруппируйте их по `card.column`.
    """
    cards = services.list_card_schemas(db, actor, board)
    counts = Counter(card.column for card in cards)
    return schemas.Board(
        stream=services.stream_schema(actor.stream),
        accept_threshold=board.accept_threshold,
        reject_threshold=board.reject_threshold,
        columns=[
            schemas.BoardColumn(
                id=column, title=title, description=description, cards_count=counts.get(column, 0)
            )
            for column, title, description in services.COLUMNS
        ],
        cards_count=len(cards),
        members_count=services.members_count(db, actor.stream_id),
    )
