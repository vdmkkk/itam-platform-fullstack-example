"""Enumerations shared by the database models and the API schemas.

Each one becomes a named schema in OpenAPI, so codegen turns it into a
TypeScript union such as `type CardType = "event" | "idea" | "question"`.
"""

import enum


class CardType(str, enum.Enum):
    """What a card is about. The author picks it and can change it at any time.

    - `event`: something that happens on a date, like a meetup, a deadline or a hackathon.
    - `idea`: a proposal for the stream to vote on.
    - `question`: something you want answered.
    """

    event = "event"
    idea = "idea"
    question = "question"


class CardColumn(str, enum.Enum):
    """The board column a card is drawn in.

    `event`, `idea` and `question` mirror the card's `type`. A card moves to
    `accepted` or `rejected` when its score reaches a vote threshold (see
    `GET /api/board`). It keeps its original `type` while it is there.
    """

    event = "event"
    idea = "idea"
    question = "question"
    accepted = "accepted"
    rejected = "rejected"


class VoteValue(str, enum.Enum):
    """A vote on a card. `up` adds 1 to the card's score and `down` subtracts 1."""

    up = "up"
    down = "down"


class CardSort(str, enum.Enum):
    """The order of a card list.

    - `new`: newest first (the default).
    - `old`: oldest first.
    - `top`: highest score first. Cards with the same score are newest first.
    """

    new = "new"
    old = "old"
    top = "top"
