from collections import Counter

from fastapi import APIRouter

from app import schemas, services
from app.deps import BoardThresholds, CurrentActor, DbSession
from app.docs import AUTH_ERRORS

router = APIRouter(tags=["Board"])


@router.get(
    "/board",
    response_model=schemas.Board,
    summary="Board overview: columns, thresholds, your stream",
    responses=AUTH_ERRORS,
)
def get_board(actor: CurrentActor, db: DbSession, board: BoardThresholds) -> schemas.Board:
    """Everything about the board **except** the cards themselves:

    - `stream`: the work group this board belongs to (yours);
    - `accept_threshold` / `reject_threshold`: how many net votes move a card to
      *accepted* / *rejected*;
    - `columns`: all five columns in display order, with how many cards each holds right now.

    Then load the cards with `GET /api/cards` and group them by `card.column`.
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
