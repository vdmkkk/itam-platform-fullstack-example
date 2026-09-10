"""Enumerations shared by the database models and the API schemas.

Each one becomes a named schema in OpenAPI, so codegen turns it into a
TypeScript union such as `type CardType = "event" | "idea" | "question"`.
The docstrings become the schema descriptions students read in Swagger,
so they are in Russian.
"""

import enum


class CardType(str, enum.Enum):
    """О чём карточка. Тип выбирает автор и может поменять его в любой момент.

    - `event`: то, что происходит в определённый день: встреча, дедлайн, хакатон.
    - `idea`: предложение, за которое голосуют участники.
    - `question`: то, на что вы хотите получить ответ.
    """

    event = "event"
    idea = "idea"
    question = "question"


class CardColumn(str, enum.Enum):
    """Колонка доски, в которой рисуется карточка.

    `event`, `idea` и `question` повторяют `type` карточки. В `accepted` или
    `rejected` карточка переходит, когда её счёт достигает порога (см.
    `GET /api/board`), и сохраняет при этом свой исходный `type`.
    """

    event = "event"
    idea = "idea"
    question = "question"
    accepted = "accepted"
    rejected = "rejected"


class VoteValue(str, enum.Enum):
    """Голос за карточку: `up` добавляет к её счёту 1, `down` отнимает 1."""

    up = "up"
    down = "down"


class CardSort(str, enum.Enum):
    """Порядок списка карточек.

    - `new`: сначала новые (по умолчанию).
    - `old`: сначала старые.
    - `top`: сначала с наибольшим счётом; при равном счёте — сначала новые.
    """

    new = "new"
    old = "old"
    top = "top"
