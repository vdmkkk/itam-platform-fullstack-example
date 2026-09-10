"""Request and response bodies.

Every field is documented. Students read these descriptions in Swagger, and
codegen turns them into comments on their TypeScript types.

Conventions:

- Response models have no defaults, so every field is *required* in the
  schema. It is always present in the JSON, possibly as `null`.
- Update models give non-nullable fields `Field(default=None)`. Such a field
  may be omitted, but an explicit `null` is rejected.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

from app.enums import CardColumn, CardType, VoteValue

PREVIEW_MAX_LENGTH = 300_000
AVATAR_MAX_LENGTH = 150_000
IMAGE_PREFIXES = ("http://", "https://", "data:image/")
TELEGRAM_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")

EXAMPLE_UUID = "3f8e9c1a-5b2d-4e7f-9a61-2c4b8d0e1f23"
EXAMPLE_TIME = "2026-09-10T12:00:00Z"


def _thousands(value: int) -> str:
    """300000 -> '300 000'."""
    return f"{value:_}".replace("_", " ")


def _no_default(schema: dict[str, Any]) -> None:
    """Hide `default: null` for fields that may be omitted but can't be null."""
    schema.pop("default", None)


def _empty_to_none(value: str | None) -> str | None:
    return value or None


def _check_image(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith(IMAGE_PREFIXES):
        raise PydanticCustomError(
            "image_string",
            "Must be an image link starting with http:// or https://, or a data:image/... URI",
        )
    return value


def _check_telegram(value: str | None) -> str | None:
    if not value:
        return None
    username = value.removeprefix("@")
    if not TELEGRAM_RE.fullmatch(username):
        raise PydanticCustomError(
            "telegram",
            "A Telegram username is 5-32 letters, digits or underscores (the leading @ is optional)",
        )
    return username


class RequestBody(BaseModel):
    """Base for request bodies: trims strings and rejects unknown (misspelled) fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Every error response looks like this."""

    detail: str = Field(
        description="What went wrong, as a sentence you can show to a person.",
        examples=["Card not found."],
    )


class FieldError(BaseModel):
    """A problem with one specific input."""

    field: str = Field(
        description=(
            "Which input the problem is about. It can be a body field (`title`, `email`; "
            "nested fields use dots, like `items.0.name`), a query or path parameter name, "
            "or `body` for the request body as a whole."
        ),
        examples=["title"],
    )
    message: str = Field(
        description="What is wrong with it. Show it next to the matching form input.",
        examples=["This field is required"],
    )


class ValidationErrorResponse(BaseModel):
    """Returned with 422 (invalid data) and some 409s (e.g. an email that is already taken).

    `detail` sums up every problem in one sentence. `errors` lists them one
    by one, so a form can highlight the right inputs.
    """

    detail: str = Field(
        description="All problems, in one readable sentence.",
        examples=["title: This field is required; type: Input should be 'event', 'idea' or 'question'"],
    )
    errors: list[FieldError] = Field(description="The same problems, one per input.")


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class Stream(BaseModel):
    """Your work group (cohort).

    Everything you can see through this API belongs to your stream. Other
    streams have their own boards, and you can't see them.
    """

    id: uuid.UUID | None = Field(
        description=(
            "Stream id on the course platform. `null` if you are enrolled without a stream: "
            "everyone without a stream shares a separate board."
        ),
        examples=["7c2a41e0-93d4-4b8e-8f0c-5a1d2e3f4b5c"],
    )
    code: str | None = Field(description="Short stream code.", examples=["26F"])
    title: str | None = Field(
        description="Title given by the course team. Often `null`, so display `name` instead.",
        examples=["Осенний поток 2026"],
    )
    name: str = Field(
        description="A ready-to-display name: `title`, or `code` when there is no title.",
        examples=["Осенний поток 2026"],
    )


class User(BaseModel):
    """A member of your stream, as everyone else sees them.

    Used as the author of cards and comments and in the people list. The
    email is private and appears only in your own `Profile`.
    """

    id: uuid.UUID = Field(
        description=(
            "User id in this API. Use it with `GET /api/users/{user_id}` and "
            "`GET /api/cards?author_id=...`."
        ),
        examples=[EXAMPLE_UUID],
    )
    name: str = Field(description="Display name.", examples=["Аня Петрова"])
    avatar_url: str | None = Field(
        description=(
            "Avatar as a string you can put straight into `<img src>`: an http(s) link or a "
            "`data:image/...` URI. `null` means no avatar, so show initials instead."
        ),
        examples=["https://courses.salut.uno/api/v1/media/avatars/anya.png"],
    )
    status: str | None = Field(
        description="Short status line, like in a messenger.", examples=["Ищу команду на хакатон"]
    )
    bio: str | None = Field(description="A few words about themselves.", examples=["Учу React по вечерам."])
    telegram: str | None = Field(
        description="Telegram username without the `@`.", examples=["anya_codes"]
    )
    is_demo: bool = Field(
        description=(
            "`true` for the demo people who fill every new board with examples. They are not "
            "real classmates."
        ),
        examples=[False],
    )
    is_me: bool = Field(description="`true` if this is you.", examples=[False])
    created_at: dt.datetime = Field(
        description="When they first appeared in this API (ISO-8601, UTC).", examples=[EXAMPLE_TIME]
    )


class UserDetail(User):
    """A member of your stream, with their activity counters."""

    cards_count: int = Field(description="How many cards they have posted.", examples=[4])
    comments_count: int = Field(description="How many comments they have written.", examples=[11])
    total_score: int = Field(
        description="The sum of the scores of all their cards.", examples=[7]
    )


class Profile(BaseModel):
    """Your own profile.

    It starts with your name, email and avatar from the course platform. After
    that it belongs to you: editing it here doesn't change the platform, and
    changes on the platform don't overwrite it.
    """

    id: uuid.UUID = Field(description="Your user id in this API.", examples=[EXAMPLE_UUID])
    name: str = Field(description="Display name.", examples=["Аня Петрова"])
    email: str | None = Field(
        description="Your email. Only you can see it. It must be unique within your stream.",
        examples=["anya@example.com"],
    )
    avatar_url: str | None = Field(
        description="Avatar: an http(s) image link or a `data:image/...` URI.",
        examples=["https://courses.salut.uno/api/v1/media/avatars/anya.png"],
    )
    status: str | None = Field(description="Short status line.", examples=["Ищу команду на хакатон"])
    bio: str | None = Field(description="About you.", examples=["Учу React по вечерам."])
    telegram: str | None = Field(description="Telegram username without the `@`.", examples=["anya_codes"])
    stream: Stream = Field(description="The stream you are in.")
    created_at: dt.datetime = Field(
        description="When you first used this API (ISO-8601, UTC).", examples=[EXAMPLE_TIME]
    )
    updated_at: dt.datetime = Field(
        description="When the profile was last changed (ISO-8601, UTC).", examples=[EXAMPLE_TIME]
    )


class ProfileUpdate(RequestBody):
    """Change your profile. Send only the fields you want to change.

    - Omitted fields stay as they are.
    - `null` (or an empty string) clears an optional field.
    - `name` can be changed but not cleared.
    """

    name: str = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Display name, 1-80 characters.",
        examples=["Аня Петрова"],
        json_schema_extra=_no_default,
    )
    email: EmailStr | None = Field(
        default=None,
        description=(
            "A valid email address, unique within your stream. If a classmate already uses it, "
            "you get 409 `This email is already in use`."
        ),
        examples=["anya@example.com"],
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=AVATAR_MAX_LENGTH,
        description=(
            f"An http(s) image link or a `data:image/...;base64,...` URI, up to "
            f"{_thousands(AVATAR_MAX_LENGTH)} characters. Your avatar is shown on every card and "
            "comment you post, so keep it small."
        ),
        examples=["https://i.pravatar.cc/150?img=5"],
    )
    status: str | None = Field(
        default=None, max_length=100, description="Short status line, up to 100 characters.",
        examples=["Ищу команду на хакатон"],
    )
    bio: str | None = Field(
        default=None, max_length=1000, description="About you, up to 1000 characters.",
        examples=["Учу React по вечерам."],
    )
    telegram: str | None = Field(
        default=None,
        max_length=33,
        description=(
            "Telegram username: 5-32 letters, digits or underscores. The leading `@` is optional "
            "and is stripped."
        ),
        examples=["@anya_codes"],
    )

    _empty_texts = field_validator("status", "bio")(_empty_to_none)
    _avatar = field_validator("avatar_url")(_check_image)
    _telegram = field_validator("telegram")(_check_telegram)

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class Comment(BaseModel):
    """A comment on a card. Comments are flat: you can't reply to a comment."""

    id: uuid.UUID = Field(description="Comment id.", examples=[EXAMPLE_UUID])
    card_id: uuid.UUID = Field(description="The card it belongs to.", examples=[EXAMPLE_UUID])
    text: str = Field(description="The comment text.", examples=["Буду! А запись будет?"])
    author: User = Field(description="Who wrote it.")
    is_mine: bool = Field(
        description="`true` if you wrote it, meaning you can edit or delete it.", examples=[False]
    )
    created_at: dt.datetime = Field(description="When it was posted (ISO-8601, UTC).", examples=[EXAMPLE_TIME])
    updated_at: dt.datetime = Field(
        description="When it was last edited (ISO-8601, UTC). Equal to `created_at` if it was never edited.",
        examples=[EXAMPLE_TIME],
    )


class CommentCreate(RequestBody):
    """A new comment."""

    text: str = Field(
        min_length=1, max_length=2000, description="Comment text, 1-2000 characters.",
        examples=["Классная идея, я за!"],
    )


class CommentUpdate(RequestBody):
    """New text for your comment."""

    text: str = Field(
        min_length=1, max_length=2000, description="Comment text, 1-2000 characters.",
        examples=["Классная идея, я за! (upd: уже проголосовал)"],
    )


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

_PREVIEW_DESCRIPTION = (
    "A picture for the card, as a string. Use an `https://...` image link, or a "
    "`data:image/...;base64,...` URI (for example from `FileReader.readAsDataURL`). "
    f"Up to {_thousands(PREVIEW_MAX_LENGTH)} characters, so use links for big images. "
    "An empty string counts as `null`."
)

_DATE_DESCRIPTION = (
    "An optional date in `YYYY-MM-DD` format, which is exactly what `<input type=\"date\">` "
    "gives you. Handy for events."
)


class Card(BaseModel):
    """A card on the board, with everything needed to draw it.

    **Which column?** Use `column`:

    - `accepted` when `score >= accept_threshold`;
    - `rejected` when `score <= -reject_threshold`;
    - otherwise the card's `type` (`event`, `idea` or `question`).

    This is computed live on every request. If votes change, the card moves.
    """

    id: uuid.UUID = Field(description="Card id.", examples=[EXAMPLE_UUID])
    title: str = Field(description="Card title.", examples=["Тёмная тема для доски"])
    type: CardType = Field(
        description=(
            "The kind of card, chosen by its author. It stays the same when the card is "
            "accepted or rejected."
        ),
        examples=[CardType.idea],
    )
    description: str | None = Field(
        description="Longer text, or `null`.",
        examples=["Вечером глаза устают от белого фона. Давайте добавим переключатель темы!"],
    )
    preview: str | None = Field(
        description="A picture you can put straight into `<img src>`, or `null`.",
        examples=["https://picsum.photos/seed/itam/640/360"],
    )
    date: dt.date | None = Field(description="Date in `YYYY-MM-DD` format, or `null`.", examples=["2026-10-01"])
    column: CardColumn = Field(
        description="The column to draw the card in (see the rules above).",
        examples=[CardColumn.accepted],
    )
    is_accepted: bool = Field(
        description="`true` when the score has reached the accept threshold.", examples=[True]
    )
    is_rejected: bool = Field(
        description="`true` when the score has fallen to minus the reject threshold.", examples=[False]
    )
    upvotes: int = Field(description="How many people voted `up`.", examples=[6])
    downvotes: int = Field(description="How many people voted `down`.", examples=[1])
    votes_count: int = Field(description="All votes: `upvotes + downvotes`.", examples=[7])
    score: int = Field(description="`upvotes - downvotes`.", examples=[5])
    votes_to_accept: int = Field(
        description=(
            "How many more net upvotes the card needs to be accepted: "
            "`max(0, accept_threshold - score)`. `0` when it is accepted."
        ),
        examples=[0],
    )
    votes_to_reject: int = Field(
        description=(
            "How many more net downvotes would get it rejected: "
            "`max(0, score + reject_threshold)`. `0` when it is rejected."
        ),
        examples=[10],
    )
    comments_count: int = Field(description="How many comments it has.", examples=[2])
    my_vote: VoteValue | None = Field(
        description=(
            "How *you* voted: `up`, `down`, or `null` if you haven't voted. Always `null` on "
            "your own cards, because you can't vote on them."
        ),
        examples=[VoteValue.up],
    )
    is_mine: bool = Field(
        description=(
            "`true` if you are the author. Only the author can edit or delete a card, and "
            "nobody can vote on their own cards."
        ),
        examples=[False],
    )
    author: User = Field(description="Who posted the card.")
    created_at: dt.datetime = Field(description="When it was posted (ISO-8601, UTC).", examples=[EXAMPLE_TIME])
    updated_at: dt.datetime = Field(
        description="When its content was last edited (ISO-8601, UTC). Votes and comments don't change it.",
        examples=[EXAMPLE_TIME],
    )


class CardDetail(Card):
    """A card with its comments. It has every `Card` field plus `comments`."""

    comments: list[Comment] = Field(description="All comments, oldest first.")


class CardCreate(RequestBody):
    """A new card. Only `title` and `type` are required."""

    title: str = Field(
        min_length=1,
        max_length=120,
        description="Card title, 1-120 characters. Leading and trailing spaces are trimmed.",
        examples=["Сходить на хакатон ITAM"],
    )
    type: CardType = Field(
        description=(
            "Which column the card starts in: `event`, `idea` or `question`. You can't create "
            "an `accepted` or `rejected` card: only votes move cards there."
        ),
        examples=[CardType.idea],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Longer text, up to 5000 characters. An empty string counts as `null`.",
        examples=["Собираем команду из 3-4 человек, опыт не важен."],
    )
    preview: str | None = Field(
        default=None, max_length=PREVIEW_MAX_LENGTH, description=_PREVIEW_DESCRIPTION,
        examples=["https://picsum.photos/seed/itam/640/360"],
    )
    date: dt.date | None = Field(default=None, description=_DATE_DESCRIPTION, examples=["2026-10-01"])

    _empty_description = field_validator("description")(_empty_to_none)
    _preview = field_validator("preview")(_check_image)


class CardUpdate(RequestBody):
    """Change your card. Send only the fields you want to change.

    - Omitted fields stay as they are.
    - `null` clears `description`, `preview` or `date`.
    - `title` and `type` can be changed but not cleared.

    Changing `type` moves the card between the `event`, `idea` and `question`
    columns. It doesn't affect votes, so an accepted card stays accepted.
    """

    title: str = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Card title, 1-120 characters.",
        examples=["Сходить на хакатон ITAM всей командой"],
        json_schema_extra=_no_default,
    )
    type: CardType = Field(
        default=None,
        description="New type: `event`, `idea` or `question`.",
        examples=[CardType.event],
        json_schema_extra=_no_default,
    )
    description: str | None = Field(
        default=None, max_length=5000, description="Longer text, or `null` to clear it."
    )
    preview: str | None = Field(
        default=None, max_length=PREVIEW_MAX_LENGTH, description=_PREVIEW_DESCRIPTION
    )
    date: dt.date | None = Field(default=None, description=_DATE_DESCRIPTION)

    _empty_description = field_validator("description")(_empty_to_none)
    _preview = field_validator("preview")(_check_image)


class VoteRequest(RequestBody):
    """Your vote. Sending it again with the other value changes your vote."""

    value: VoteValue = Field(description="`up` or `down`.", examples=[VoteValue.up])


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


class BoardColumn(BaseModel):
    """One column of the board."""

    id: CardColumn = Field(description="Column id, the same value as `Card.column`.", examples=[CardColumn.idea])
    title: str = Field(description="A human-readable title.", examples=["Ideas"])
    description: str = Field(
        description="What goes into this column.", examples=["Proposals for the stream to vote on."]
    )
    cards_count: int = Field(description="How many cards are in it right now.", examples=[3])


class Board(BaseModel):
    """The board as a whole: its columns, the vote thresholds and your stream."""

    stream: Stream = Field(description="The stream this board belongs to (yours).")
    accept_threshold: int = Field(
        description="A card is accepted when `score >= accept_threshold`.", examples=[5]
    )
    reject_threshold: int = Field(
        description="A card is rejected when `score <= -reject_threshold`.", examples=[5]
    )
    columns: list[BoardColumn] = Field(
        description="All five columns, in display order: event, idea, question, accepted, rejected."
    )
    cards_count: int = Field(description="Cards on the board in total.", examples=[8])
    members_count: int = Field(
        description="Real people in your stream who are known to this API (demo people excluded).",
        examples=[17],
    )


# ---------------------------------------------------------------------------
# Admin and system
# ---------------------------------------------------------------------------


class BoardSettings(BaseModel):
    """Vote thresholds, shared by all streams."""

    accept_threshold: int = Field(description="`score >= accept_threshold` means accepted.", examples=[5])
    reject_threshold: int = Field(description="`score <= -reject_threshold` means rejected.", examples=[5])
    updated_at: dt.datetime = Field(description="When they were last changed.", examples=[EXAMPLE_TIME])


class BoardSettingsUpdate(RequestBody):
    """New thresholds. Send one or both. They apply immediately to every card in every stream."""

    accept_threshold: int = Field(
        default=None, ge=1, le=1000, description="Positive integer.", examples=[3],
        json_schema_extra=_no_default,
    )
    reject_threshold: int = Field(
        default=None, ge=1, le=1000, description="Positive integer.", examples=[3],
        json_schema_extra=_no_default,
    )


class AdminStream(BaseModel):
    """A stream this API has seen, with activity counters."""

    id: uuid.UUID | None = Field(description="Platform stream id, or `null` for students without a stream.")
    code: str | None = Field(description="Stream code.", examples=["26F"])
    title: str | None = Field(description="Stream title.", examples=["Осенний поток 2026"])
    name: str = Field(description="`title` or `code`.", examples=["Осенний поток 2026"])
    members_count: int = Field(description="Real people (demo people excluded).", examples=[17])
    cards_count: int = Field(description="Cards, including demo cards.", examples=[42])
    comments_count: int = Field(description="Comments.", examples=[120])
    votes_count: int = Field(description="Votes.", examples=[300])
    first_seen_at: dt.datetime = Field(description="When the first student of the stream showed up.")


class Health(BaseModel):
    status: str = Field(description="`ok` when the API and its database are up.", examples=["ok"])
